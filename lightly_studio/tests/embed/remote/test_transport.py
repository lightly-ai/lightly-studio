from __future__ import annotations

import email.utils
import time
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import httpx
import numpy as np
import pytest
from fastapi.testclient import TestClient
from lightly_studio_serve import protocol, server
from lightly_studio_serve.embedder import (
    Capability,
    ImageBytesEmbedder,
    TextEmbedder,
    VideoBytesEmbedder,
)
from lightly_studio_serve.protocol import ServerLimits
from lightly_studio_serve.types import EmbeddingResult, EmbeddingSpaceSpec
from pytest_mock import MockerFixture

from lightly_studio.embed.remote import transport
from lightly_studio.embed.remote.errors import (
    RemoteEmbedderAuthError,
    RemoteEmbedderBatchTooLargeError,
    RemoteEmbedderCapabilityError,
    RemoteEmbedderProtocolError,
    RemoteEmbedderUnreachableError,
)
from lightly_studio.embed.remote.transport import RemoteTransport

SPACE_KEY = "acme/model@v1"
DIMENSION = 2
API_KEY = "s3cret"
BASE_URL = "http://embedding-server"

# The date form of `Retry-After`, far enough in the future to be over the cap.
HTTP_DATE_FAR_FUTURE = "Wed, 21 Oct 2099 07:28:00 GMT"
HTTP_DATE_PAST = "Wed, 21 Oct 2015 07:28:00 GMT"


class FakeTextEmbedder(TextEmbedder):
    """Returns one fixed row per text and records the texts it was handed."""

    def __init__(self) -> None:
        self.received: list[str] = []

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        return EmbeddingSpaceSpec(space_key=SPACE_KEY, dimension=DIMENSION)

    def embed_text(self, texts: list[str]) -> EmbeddingResult:
        self.received = texts
        return _rows(count=len(texts))


class FakeBytesEmbedder(ImageBytesEmbedder, VideoBytesEmbedder):
    """Embeds images and videos, recording the bytes it was handed."""

    def __init__(self) -> None:
        self.received: list[bytes] = []

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        return EmbeddingSpaceSpec(space_key=SPACE_KEY, dimension=DIMENSION)

    def embed_image_bytes(self, images: list[bytes]) -> EmbeddingResult:
        self.received = images
        return _rows(count=len(images))

    def embed_video_bytes(self, videos: list[bytes]) -> EmbeddingResult:
        self.received = videos
        return _rows(count=len(videos))


class TestRemoteTransport:
    def test_describe(self) -> None:
        embedder = FakeTextEmbedder()
        with TestClient(server.create_app(embedder=embedder)) as client:
            description = RemoteTransport(client=client).describe()

        assert description.protocol_version == protocol.PROTOCOL_VERSION
        assert description.space_key == SPACE_KEY
        assert description.dimension == DIMENSION
        assert description.ready
        assert description.capabilities == [Capability.TEXT]

    def test_describe__protocol_version_mismatch(self) -> None:
        # A server of another major version is the one most likely to answer another
        # shape. The version must still be what the message names, so the check runs
        # before the model. `DescribeResponse` carries no `model` field: this body is
        # deliberately one that version 1 cannot read.
        body = {"protocol_version": "2.0", "model": {"name": "acme"}}
        client = _client_answering(responses=[httpx.Response(status_code=200, json=body)])

        with pytest.raises(RemoteEmbedderProtocolError, match=r"speaks protocol version 2\.0"):
            RemoteTransport(client=client).describe()

    def test_describe__minor_version_is_accepted(self) -> None:
        body = _describe_body(capabilities=["text"])
        body["protocol_version"] = "1.7"
        client = _client_answering(responses=[httpx.Response(status_code=200, json=body)])

        assert RemoteTransport(client=client).describe().protocol_version == "1.7"

    def test_describe__body_not_json(self) -> None:
        client = _client_answering(
            responses=[httpx.Response(status_code=200, text="<html>hello</html>")]
        )

        with pytest.raises(RemoteEmbedderProtocolError, match="not JSON"):
            RemoteTransport(client=client).describe()

    def test_embed_texts(self) -> None:
        embedder = FakeTextEmbedder()
        with TestClient(server.create_app(embedder=embedder)) as client:
            response = RemoteTransport(client=client).embed_texts(texts=["a dog", "a cat"])

        assert embedder.received == ["a dog", "a cat"]
        assert response.space_key == SPACE_KEY
        assert response.kept_indices == [0, 1]
        assert response.embeddings == [[0.5, -0.5], [0.5, -0.5]]

    def test_embed_texts__sends_the_token(self) -> None:
        with TestClient(server.create_app(embedder=FakeTextEmbedder(), api_key=API_KEY)) as client:
            response = RemoteTransport(client=client, api_key=API_KEY).embed_texts(texts=["a dog"])

        assert response.kept_indices == [0]

    def test_embed_texts__no_token(self) -> None:
        app = server.create_app(embedder=FakeTextEmbedder(), api_key=API_KEY)
        with TestClient(app) as client, pytest.raises(RemoteEmbedderAuthError) as error:
            RemoteTransport(client=client).embed_texts(texts=["a dog"])

        assert "did not accept the token" in str(error.value)

    def test_embed_texts__batch_over_the_limit(self) -> None:
        app = server.create_app(embedder=FakeTextEmbedder(), limits=ServerLimits(max_batch_size=1))
        with TestClient(app) as client, pytest.raises(RemoteEmbedderBatchTooLargeError) as error:
            RemoteTransport(client=client).embed_texts(texts=["a dog", "a cat"])

        assert "over one of its limits" in str(error.value)

    def test_embed_texts__capability_not_served(self) -> None:
        client = _client_answering(responses=[httpx.Response(status_code=501, json={})])

        with pytest.raises(RemoteEmbedderCapabilityError, match="does not serve that input kind"):
            RemoteTransport(client=client).embed_texts(texts=["a dog"])

    def test_embed_texts__server_error(self) -> None:
        answer = httpx.Response(status_code=500, json={"detail": "The embedder raised OSError."})
        client = _client_answering(responses=[answer])

        with pytest.raises(RemoteEmbedderProtocolError, match="answered 500"):
            RemoteTransport(client=client).embed_texts(texts=["a dog"])

    def test_embed_texts__body_breaks_a_rule(self) -> None:
        # One vector for two kept indices. The wire model refuses to line them up.
        body = {
            "space_key": SPACE_KEY,
            "dimension": DIMENSION,
            "kept_indices": [0, 1],
            "embeddings": [[0.5, -0.5]],
        }
        client = _client_answering(responses=[httpx.Response(status_code=200, json=body)])

        with pytest.raises(RemoteEmbedderProtocolError, match="protocol does not allow"):
            RemoteTransport(client=client).embed_texts(texts=["a dog", "a cat"])

    def test_embed_texts__retries_while_busy(self, mocker: MockerFixture) -> None:
        mock_sleep = mocker.patch.object(time, "sleep")
        client = _client_answering(
            responses=[
                httpx.Response(status_code=503, headers={"Retry-After": "0"}),
                httpx.Response(status_code=503, headers={"Retry-After": "0"}),
                httpx.Response(status_code=200, json=_embeddings_body()),
            ]
        )

        response = RemoteTransport(client=client).embed_texts(texts=["a dog"])

        assert response.kept_indices == [0]
        # One wait for each of the two answers that said "later".
        assert mock_sleep.call_count == 2

    @pytest.mark.parametrize("status_code", [429, 503])
    def test_embed_texts__stays_busy(self, status_code: int, mocker: MockerFixture) -> None:
        mocker.patch.object(time, "sleep")
        answer = httpx.Response(status_code=status_code, headers={"Retry-After": "0"})
        client = _client_answering(responses=[answer])

        with pytest.raises(RemoteEmbedderUnreachableError, match="stayed busy"):
            RemoteTransport(client=client).embed_texts(texts=["a dog"])

    def test_embed_texts__connection_failed(self) -> None:
        def refuse(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Connection refused", request=request)

        client = httpx.Client(transport=httpx.MockTransport(refuse), base_url=BASE_URL)

        with pytest.raises(RemoteEmbedderUnreachableError, match="did not answer"):
            RemoteTransport(client=client).embed_texts(texts=["a dog"])

    def test_embed_image_bytes(self) -> None:
        embedder = FakeBytesEmbedder()
        with TestClient(server.create_app(embedder=embedder)) as client:
            response = RemoteTransport(client=client).embed_image_bytes(
                images=[b"\xff\xd8jpeg", b"\x89PNG"]
            )

        assert embedder.received == [b"\xff\xd8jpeg", b"\x89PNG"]
        assert response.kept_indices == [0, 1]

    def test_embed_image_bytes__empty(self) -> None:
        # httpx writes no body at all for a multipart request without parts, so the
        # transport refuses the batch before it sends. This client never answers.
        client = _client_answering(responses=[])

        with pytest.raises(ValueError, match="empty batch"):
            RemoteTransport(client=client).embed_image_bytes(images=[])

    def test_embed_image_bytes__route_not_mounted(self) -> None:
        # A server that mounts only the routes of its own capabilities answers 404 where
        # the protocol names 501. Both say the same thing to a client.
        embedder = FakeTextEmbedder()
        with (
            TestClient(server.create_app(embedder=embedder)) as client,
            pytest.raises(RemoteEmbedderCapabilityError, match="does not serve that path"),
        ):
            RemoteTransport(client=client).embed_image_bytes(images=[b"\xff\xd8jpeg"])

    def test_embed_texts__broken_rules_are_cut(self) -> None:
        # Pydantic gives one error per bad element of a list, so a long batch would
        # otherwise give an exception as long as the batch.
        body = _embeddings_body()
        body["kept_indices"] = [-1] * 200
        client = _client_answering(responses=[httpx.Response(status_code=200, json=body)])

        with pytest.raises(RemoteEmbedderProtocolError) as error:
            RemoteTransport(client=client).embed_texts(texts=["a dog"])

        assert str(error.value).endswith("...")
        assert len(str(error.value)) < 2 * transport._MAX_DETAIL_CHARS

    def test_embed_video_bytes(self) -> None:
        embedder = FakeBytesEmbedder()
        with TestClient(server.create_app(embedder=embedder)) as client:
            response = RemoteTransport(client=client).embed_video_bytes(videos=[b"\x00\x00mp4"])

        assert embedder.received == [b"\x00\x00mp4"]
        assert response.kept_indices == [0]

    def test_requests_use_their_capability_timeout(self) -> None:
        sent: list[object] = []
        remote = RemoteTransport(client=_timeout_recording_client(sent=sent))

        remote.describe()
        remote.embed_texts(texts=["a dog"])
        remote.embed_image_bytes(images=[b"jpeg"])
        remote.embed_video_bytes(videos=[b"mp4"])

        defaults = transport.DEFAULT_TIMEOUTS
        assert sent == [
            defaults.describe.as_dict(),
            defaults.text.as_dict(),
            defaults.image_bytes.as_dict(),
            defaults.video_bytes.as_dict(),
        ]

    def test_custom_timeout_overrides_the_client(self) -> None:
        sent: list[object] = []
        client = _timeout_recording_client(sent=sent, timeout=httpx.Timeout(0.001))
        timeouts = replace(transport.DEFAULT_TIMEOUTS, text=httpx.Timeout(1.5))

        RemoteTransport(client=client, timeouts=timeouts).embed_texts(texts=["a dog"])

        assert sent == [httpx.Timeout(1.5).as_dict()]


# The seconds form, no header, a value that is not a wait, a wait over the cap, a wait of
# zero, a date over the cap, and a date that has passed.
@pytest.mark.parametrize(
    ("header", "expected_seconds"),
    [
        ("7", 7.0),
        (None, 1.0),
        ("soon", 1.0),
        ("3600", 30.0),
        ("0", 1.0),
        (HTTP_DATE_FAR_FUTURE, 30.0),
        (HTTP_DATE_PAST, 1.0),
    ],
)
def test_retry_wait_seconds(header: str | None, expected_seconds: float) -> None:
    headers = {} if header is None else {"Retry-After": header}
    response = httpx.Response(status_code=503, headers=headers)

    assert transport._retry_wait_seconds(response=response) == expected_seconds


def test_retry_wait_seconds__http_date_is_a_deadline() -> None:
    deadline = datetime.now(tz=timezone.utc) + timedelta(seconds=5)
    response = httpx.Response(status_code=503, headers={"Retry-After": _http_date(moment=deadline)})

    assert 0.0 < transport._retry_wait_seconds(response=response) <= 5.0


def _rows(count: int) -> EmbeddingResult:
    embeddings = np.array([[0.5, -0.5]] * count, dtype=np.float32).reshape(count, DIMENSION)
    return EmbeddingResult(embeddings=embeddings, kept_indices=list(range(count)))


def _client_answering(responses: list[httpx.Response]) -> httpx.Client:
    """A client that answers each response in turn, and repeats the last one after that.

    It covers the answers that `server.create_app` cannot give, such as a wrong protocol
    version or a server that stays busy. A conforming server is tested against
    `server.create_app`.
    """
    remaining = list(responses)

    def handler(_request: httpx.Request) -> httpx.Response:
        return remaining.pop(0) if len(remaining) > 1 else remaining[0]

    return httpx.Client(transport=httpx.MockTransport(handler), base_url=BASE_URL)


def _timeout_recording_client(
    sent: list[object], timeout: httpx.Timeout | None = None
) -> httpx.Client:
    """Return a client that records each request timeout."""

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request.extensions["timeout"])
        body = (
            _describe_body(capabilities=["text"])
            if request.url.path == protocol.DESCRIBE_PATH
            else _embeddings_body()
        )
        return httpx.Response(status_code=200, json=body)

    client_timeout = timeout if timeout is not None else httpx.Timeout(5.0)
    return httpx.Client(
        transport=httpx.MockTransport(handler), base_url=BASE_URL, timeout=client_timeout
    )


def _describe_body(capabilities: list[str]) -> dict[str, object]:
    return {
        "protocol_version": protocol.PROTOCOL_VERSION,
        "space_key": SPACE_KEY,
        "dimension": DIMENSION,
        "ready": True,
        "capabilities": capabilities,
        "limits": {"max_batch_size": 999, "max_request_bytes": 1024},
    }


def _embeddings_body() -> dict[str, object]:
    return {
        "space_key": SPACE_KEY,
        "dimension": DIMENSION,
        "kept_indices": [0],
        "embeddings": [[0.5, -0.5]],
    }


def _http_date(moment: datetime) -> str:
    return email.utils.format_datetime(moment, usegmt=True)
