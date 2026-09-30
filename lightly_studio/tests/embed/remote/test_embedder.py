from __future__ import annotations

import logging
from collections.abc import Callable

import httpx
import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from lightly_studio_serve import protocol, server
from lightly_studio_serve.embedder import (
    ImageBytesEmbedder,
    TextEmbedder,
    VideoBytesEmbedder,
)
from lightly_studio_serve.protocol import ServerLimits
from lightly_studio_serve.types import EmbeddingResult, EmbeddingSpaceSpec
from pytest_mock import MockerFixture

from lightly_studio.dataset import env
from lightly_studio.embed import embedder_registry
from lightly_studio.embed.embedder_registry import EmbedderRegistry
from lightly_studio.embed.remote import batching, composition, embedder
from lightly_studio.embed.remote.embedder import RemoteEmbedder
from lightly_studio.embed.remote.endpoint import PersistableEmbedder, RemoteEndpoint
from lightly_studio.embed.remote.errors import (
    RemoteEmbedderBatchTooLargeError,
    RemoteEmbedderCapabilityError,
    RemoteEmbedderProtocolError,
)
from lightly_studio.embed.remote.transport import RemoteTransport
from tests.embed.remote import helpers
from tests.embed.remote.helpers import (
    BASE_URL,
    DIMENSION,
    ROW,
    SPACE_KEY,
    FakeImageEmbedder,
    FakeServer,
    FakeTextEmbedder,
    FakeTextImageEmbedder,
    FakeTextVideoEmbedder,
    FakeVideoEmbedder,
    SkippingTextEmbedder,
)


class _ExtraRoute(RemoteEmbedder):
    """A route that no server advertises, to test ``with_route``."""


class TestRemoteEmbedder:
    def test_connect__text_only(self) -> None:
        with _test_client(server.create_app(embedder=FakeTextEmbedder())) as client:
            remote = RemoteEmbedder.connect(client=client)

        assert isinstance(remote, TextEmbedder)
        assert not isinstance(remote, ImageBytesEmbedder)
        assert not isinstance(remote, VideoBytesEmbedder)

    def test_connect__image_bytes_only(self) -> None:
        with _test_client(server.create_app(embedder=FakeImageEmbedder())) as client:
            remote = RemoteEmbedder.connect(client=client)

        assert isinstance(remote, ImageBytesEmbedder)
        assert not isinstance(remote, TextEmbedder)
        assert not isinstance(remote, VideoBytesEmbedder)

    def test_connect__text_and_image_bytes(self) -> None:
        with _test_client(server.create_app(embedder=FakeTextImageEmbedder())) as client:
            remote = RemoteEmbedder.connect(client=client)

        assert isinstance(remote, TextEmbedder)
        assert isinstance(remote, ImageBytesEmbedder)
        assert type(remote).__name__ == "RemoteTextImageBytesEmbedder"

    def test_connect__reuses_the_composed_class(self) -> None:
        with _test_client(server.create_app(embedder=FakeTextImageEmbedder())) as client:
            first = RemoteEmbedder.connect(client=client)
        with _test_client(server.create_app(embedder=FakeTextImageEmbedder())) as client:
            second = RemoteEmbedder.connect(client=client)

        assert type(first) is type(second)

    def test_connect__remote_endpoint(self) -> None:
        server = FakeServer(capabilities=["text"])

        remote = RemoteEmbedder.connect(client=server.client(), api_key="secret-token")

        assert isinstance(remote, PersistableEmbedder)
        assert remote.remote_endpoint() == RemoteEndpoint(url=BASE_URL, api_key="secret-token")

    def test_remote_endpoint__class_written_by_hand(self) -> None:
        # A rebuild through `connect` would drop the methods of such a class.
        with FakeServer(capabilities=["text"]).client() as client:
            remote = _ExtraRoute(
                transport=RemoteTransport(client=client, api_key="secret-token"),
                spec=EmbeddingSpaceSpec(space_key=SPACE_KEY, dimension=DIMENSION),
                limits=ServerLimits(),
            )

        assert remote.remote_endpoint() is None

    def test_with_route(self) -> None:
        with _test_client(server.create_app(embedder=FakeTextImageEmbedder())) as client:
            remote = RemoteEmbedder.connect(client=client)

        routed = remote.with_route(route=_ExtraRoute)

        assert isinstance(routed, TextEmbedder)
        assert isinstance(routed, ImageBytesEmbedder)
        assert isinstance(routed, _ExtraRoute)
        assert type(routed).__name__ == "RemoteTextImageBytesExtraEmbedder"
        assert routed.embedding_space_spec() == remote.embedding_space_spec()
        # A build from the stored endpoint would not compose `_ExtraRoute` again
        assert routed.remote_endpoint() is None

    def test_connect__text_and_video_bytes(self) -> None:
        with _test_client(server.create_app(embedder=FakeTextVideoEmbedder())) as client:
            remote = RemoteEmbedder.connect(client=client)

        assert isinstance(remote, TextEmbedder)
        assert isinstance(remote, VideoBytesEmbedder)

    def test_connect__video_bytes_only(self) -> None:
        # Nothing in LightlyStudio resolves a video-bytes embedder yet, so the error has
        # to name that rather than let `EmbedderRegistry.register` report the symptom.
        app = server.create_app(embedder=FakeVideoEmbedder())
        with _test_client(app) as client, pytest.raises(RemoteEmbedderCapabilityError) as error:
            RemoteEmbedder.connect(client=client)

        assert "EmbedderRegistry resolves text, image_bytes" in str(error.value)

    def test_connect__nothing_routable(self) -> None:
        # `image_path` is a legal wire capability that no client of version 1 requests.
        server = FakeServer(capabilities=["image_path"])

        with pytest.raises(RemoteEmbedderCapabilityError) as error:
            RemoteEmbedder.connect(client=server.client())

        assert "routes to text, image_bytes, video_bytes" in str(error.value)

    def test_connect__url_policy_refuses_the_address(self, mocker: MockerFixture) -> None:
        # The policy runs before the first request, so the refused address is never called.
        mocker.patch.object(env, "LIGHTLY_STUDIO_REMOTE_EMBEDDER_ALLOW_PRIVATE_URLS", False)
        server = FakeServer(capabilities=["text"])

        with pytest.raises(ValueError, match="is not https"):
            RemoteEmbedder.connect(client=server.client())

        assert server.describe_calls == 0

    def test_connect__client_follows_redirects(self) -> None:
        client = httpx.Client(base_url=BASE_URL, follow_redirects=True)

        with pytest.raises(ValueError, match="must not follow redirects"):
            RemoteEmbedder.connect(client=client)

    def test_connect__server_still_loading(self, caplog: pytest.LogCaptureFixture) -> None:
        server = FakeServer(capabilities=["text"], ready=False)

        with caplog.at_level(logging.WARNING):
            RemoteEmbedder.connect(client=server.client())

        assert "still loading" in caplog.text

    def test_embedding_space_spec(self) -> None:
        with _test_client(server.create_app(embedder=FakeTextEmbedder())) as client:
            remote = RemoteEmbedder.connect(client=client)

        assert remote.embedding_space_spec() == EmbeddingSpaceSpec(
            space_key=SPACE_KEY, dimension=DIMENSION
        )

    def test_embed_text(self) -> None:
        fake = FakeTextEmbedder()
        with _test_client(server.create_app(embedder=fake)) as client:
            remote = RemoteEmbedder.connect(client=client)
            assert isinstance(remote, TextEmbedder)
            result = remote.embed_text(texts=["a dog", "a cat"])

        assert fake.batches == [["a dog", "a cat"]]
        assert result.kept_indices == [0, 1]
        assert result.embeddings.dtype == np.float32
        np.testing.assert_array_equal(result.embeddings, np.array([ROW, ROW], dtype=np.float32))

    def test_embed_text__empty_batch(self) -> None:
        fake = FakeTextEmbedder()
        with _test_client(server.create_app(embedder=fake)) as client:
            remote = RemoteEmbedder.connect(client=client)
            assert isinstance(remote, TextEmbedder)
            result = remote.embed_text(texts=[])

        assert fake.batches == []
        assert result.kept_indices == []
        assert result.embeddings.shape == (0, DIMENSION)

    def test_embed_text__skipped_item(self) -> None:
        with _test_client(server.create_app(embedder=SkippingTextEmbedder())) as client:
            remote = RemoteEmbedder.connect(client=client)
            assert isinstance(remote, TextEmbedder)
            result = remote.embed_text(texts=["a dog", "a broken input", "a cat"])

        assert result.kept_indices == [0, 2]
        assert result.embeddings.shape == (2, DIMENSION)

    def test_embed_text__splits_the_batch(self) -> None:
        # Three chunks of at most two texts. The fake skips the second item of each, so
        # the merged indices only line up when every chunk is offset by its own start.
        fake = SkippingTextEmbedder()
        app = server.create_app(embedder=fake, limits=ServerLimits(max_batch_size=2))
        with _test_client(app) as client:
            remote = RemoteEmbedder.connect(client=client)
            assert isinstance(remote, TextEmbedder)
            result = remote.embed_text(texts=["one", "two", "three", "four", "five"])

        assert fake.batches == [["one", "two"], ["three", "four"], ["five"]]
        assert result.kept_indices == [0, 2, 4]
        assert result.embeddings.shape == (3, DIMENSION)

    def test_embed_text__splits_again_on_413(self, mocker: MockerFixture) -> None:
        # With no envelope in the estimate, four texts fit the limit, but the body does not.
        mocker.patch.object(batching, "ITEM_ENVELOPE_BYTES", 0)
        fake = SkippingTextEmbedder()
        app = server.create_app(embedder=fake, limits=ServerLimits(max_request_bytes=4010))
        texts = [letter * 1000 for letter in "abcd"]
        with _test_client(app) as client:
            remote = RemoteEmbedder.connect(client=client)
            assert isinstance(remote, TextEmbedder)
            result = remote.embed_text(texts=texts)

        assert fake.batches == [texts[:2], texts[2:]]
        assert result.kept_indices == [0, 2]

    def test_embed_text__one_item_too_large(self) -> None:
        app = server.create_app(
            embedder=FakeTextEmbedder(), limits=ServerLimits(max_request_bytes=1000)
        )
        with _test_client(app) as client:
            remote = RemoteEmbedder.connect(client=client)
            assert isinstance(remote, TextEmbedder)

            with pytest.raises(RemoteEmbedderBatchTooLargeError):
                remote.embed_text(texts=["a dog", "a" * 2000])

    def test_embed_text__other_space_key(self) -> None:
        body = helpers.embeddings_body(
            kept_indices=[0], embeddings=[ROW], space_key="acme/model@v2"
        )
        server = FakeServer(
            capabilities=["text"], answer=httpx.Response(status_code=200, json=body)
        )
        remote = RemoteEmbedder.connect(client=server.client())
        assert isinstance(remote, TextEmbedder)

        with pytest.raises(RemoteEmbedderProtocolError, match="/v1/describe reported"):
            remote.embed_text(texts=["a dog"])

    def test_embed_text__other_dimension(self) -> None:
        body = helpers.embeddings_body(kept_indices=[0], embeddings=[[0.5, -0.5, 0.5]], dimension=3)
        server = FakeServer(
            capabilities=["text"], answer=httpx.Response(status_code=200, json=body)
        )
        remote = RemoteEmbedder.connect(client=server.client())
        assert isinstance(remote, TextEmbedder)

        with pytest.raises(RemoteEmbedderProtocolError, match="dimension 3"):
            remote.embed_text(texts=["a dog"])

    def test_embed_text__kept_index_past_the_request(self) -> None:
        body = helpers.embeddings_body(kept_indices=[0, 5], embeddings=[ROW, ROW])
        server = FakeServer(
            capabilities=["text"], answer=httpx.Response(status_code=200, json=body)
        )
        remote = RemoteEmbedder.connect(client=server.client())
        assert isinstance(remote, TextEmbedder)

        with pytest.raises(RemoteEmbedderProtocolError, match="carried 2 items"):
            remote.embed_text(texts=["a dog", "a cat"])

    def test_embed_text__advertised_route_refused(self) -> None:
        server = FakeServer(capabilities=["text"], answer=httpx.Response(status_code=501, json={}))
        remote = RemoteEmbedder.connect(client=server.client())
        assert isinstance(remote, TextEmbedder)

        with pytest.raises(RemoteEmbedderProtocolError, match="refuses to serve it"):
            remote.embed_text(texts=["a dog"])

        assert server.describe_calls == 2

    def test_embed_text__advertised_route_refused_and_describe_fails(self) -> None:
        # A second read that fails says nothing, so the refusal reaches the caller.
        server = FakeServer(capabilities=["text"], answer=httpx.Response(status_code=501, json={}))
        remote = RemoteEmbedder.connect(client=server.client())
        assert isinstance(remote, TextEmbedder)
        server.describe_answer = httpx.Response(status_code=500, json={"detail": "gone"})

        with pytest.raises(RemoteEmbedderCapabilityError, match="answered 501"):
            remote.embed_text(texts=["a dog"])

    def test_embed_text__capability_dropped(self) -> None:
        server = FakeServer(capabilities=["text"], answer=httpx.Response(status_code=501, json={}))
        remote = RemoteEmbedder.connect(client=server.client())
        assert isinstance(remote, TextEmbedder)
        server.capabilities = []

        with pytest.raises(RemoteEmbedderCapabilityError, match="no longer serves text"):
            remote.embed_text(texts=["a dog"])

        assert server.describe_calls == 2

    def test_embed_image_bytes__splits_on_request_bytes(self) -> None:
        # Two items fit under the limit and three do not, though `max_batch_size` allows four.
        fake = FakeImageEmbedder()
        app = server.create_app(embedder=fake, limits=ServerLimits(max_request_bytes=3000))
        images = [bytes([index]) * 1000 for index in range(4)]
        with _test_client(app) as client:
            remote = RemoteEmbedder.connect(client=client)
            assert isinstance(remote, ImageBytesEmbedder)
            result = remote.embed_image_bytes(images=images)

        assert fake.batches == [images[:2], images[2:]]
        assert result.kept_indices == [0, 1, 2, 3]

    def test_embed_image_bytes(self) -> None:
        fake = FakeImageEmbedder()
        with _test_client(server.create_app(embedder=fake)) as client:
            remote = RemoteEmbedder.connect(client=client)
            assert isinstance(remote, ImageBytesEmbedder)
            result = remote.embed_image_bytes(images=[b"\xff\xd8jpeg", b"\x89PNG"])

        assert fake.batches == [[b"\xff\xd8jpeg", b"\x89PNG"]]
        assert result.kept_indices == [0, 1]
        assert result.embeddings.shape == (2, DIMENSION)

    def test_embed_video_bytes(self) -> None:
        fake = FakeTextVideoEmbedder()
        with _test_client(server.create_app(embedder=fake)) as client:
            remote = RemoteEmbedder.connect(client=client)
            assert isinstance(remote, VideoBytesEmbedder)
            result = remote.embed_video_bytes(videos=[b"\x00\x00mp4"])

        assert fake.batches == [[b"\x00\x00mp4"]]
        assert result.kept_indices == [0]

    @pytest.mark.parametrize(
        ("capabilities", "call", "path"),
        [
            (
                ["text"],
                lambda remote: remote.embed_text(texts=["a dog"]),
                protocol.EMBED_TEXTS_PATH,
            ),
            (
                ["image_bytes"],
                lambda remote: remote.embed_image_bytes(images=[b"jpeg"]),
                protocol.EMBED_IMAGES_BYTES_PATH,
            ),
            # A video route needs a capability that the registry resolves beside it.
            (
                ["text", "video_bytes"],
                lambda remote: remote.embed_video_bytes(videos=[b"mp4"]),
                protocol.EMBED_VIDEOS_BYTES_PATH,
            ),
        ],
    )
    def test_embed__posts_to_the_route_of_the_capability(
        self, capabilities: list[str], call: Callable[[RemoteEmbedder], EmbeddingResult], path: str
    ) -> None:
        # Every route answers alike, so only the path that was asked for tells them apart.
        body = helpers.embeddings_body(kept_indices=[0], embeddings=[ROW])
        fake = FakeServer(
            capabilities=capabilities, answer=httpx.Response(status_code=200, json=body)
        )
        remote = RemoteEmbedder.connect(client=fake.client())

        call(remote)

        assert fake.paths == [protocol.DESCRIBE_PATH, path]


def test_resolvable_capabilities__match_the_registry() -> None:
    # The constant exists only because the registry cannot resolve every capability this
    # client routes to. It must not go stale when the registry gains an entry.
    routable = set(embedder._CAPABILITY_TO_BASE)

    assert routable & set(embedder_registry._CAPABILITY_TO_TYPE) == set(
        composition._RESOLVABLE_CAPABILITIES
    )


def test_register_and_resolve() -> None:
    with _test_client(server.create_app(embedder=FakeTextImageEmbedder())) as client:
        remote = RemoteEmbedder.connect(client=client)

    registry = EmbedderRegistry()
    registry.register(embedder=remote)

    # Typed as `object`, because the composed class exists only at runtime and mypy reads
    # `remote` as a plain `RemoteEmbedder`.
    text_embedder: object = registry.get_text_embedder()
    image_embedder: object = registry.get_image_bytes_embedder()

    # `register` adds the image-path capability, so the registry holds a new embedder.
    assert isinstance(text_embedder, RemoteEmbedder)
    assert text_embedder.embedding_space_spec() == remote.embedding_space_spec()
    assert image_embedder is text_embedder


def _test_client(app: FastAPI) -> TestClient:
    """A client that drives ``app`` in process and meets the URL policy.

    ``TestClient`` defaults to ``http://testserver`` and to following redirects. The policy
    reads the ``base_url`` of the client as the address of the server and refuses a client
    that follows a redirect, so both are set here rather than left at the default.
    """
    return TestClient(app, base_url=BASE_URL, follow_redirects=False)
