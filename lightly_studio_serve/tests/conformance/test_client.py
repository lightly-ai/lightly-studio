from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse, RedirectResponse

from lightly_studio_serve import protocol, server
from lightly_studio_serve.conformance import client as client_module
from lightly_studio_serve.conformance.client import ConformanceRequestError, HttpProbeClient
from lightly_studio_serve.conformance.probes import PROBES
from lightly_studio_serve.embedder import Capability
from tests.conformance import helpers
from tests.conformance.helpers import FakeEmbedder

API_KEY = "the-key"
TIMEOUT = 5.0


class TestHttpProbeClient:
    def test_init__address_that_is_no_http_url(self) -> None:
        """The opener answers nothing at all for another scheme, so this must not pass."""
        with pytest.raises(ValueError, match="must start with http"):
            HttpProbeClient(base_url="127.0.0.1:8080")

    def test_init__address_in_upper_case(self) -> None:
        """The scheme carries no case for urllib, so rejecting one would read as nonsense."""
        client = HttpProbeClient(base_url="HTTP://127.0.0.1:8080")

        assert client.base_url == "HTTP://127.0.0.1:8080"

    def test_init__api_key_over_http_to_another_host(self) -> None:
        """The token would go over the network in clear text, as it does for ``serve``."""
        with pytest.warns(UserWarning, match="clear text"):
            HttpProbeClient(base_url="http://embed.example.com", api_key=API_KEY)

    def test_get(self) -> None:
        with helpers.serving(app=server.create_app(embedder=FakeEmbedder())) as url:
            response = HttpProbeClient(base_url=f"{url}/").get(
                path=protocol.DESCRIBE_PATH, timeout=TIMEOUT
            )

        assert response.status_code == 200
        assert b'"space_key"' in response.body

    def test_post(self) -> None:
        probe = PROBES[Capability.IMAGE_BYTES]
        with helpers.serving(app=server.create_app(embedder=FakeEmbedder())) as url:
            response = HttpProbeClient(base_url=url).post(
                path=probe.path, content_type=probe.content_type, body=probe.body, timeout=TIMEOUT
            )

        assert response.status_code == 200
        assert b'"kept_indices":[0]' in response.body

    def test_get__api_key(self) -> None:
        app = server.create_app(embedder=FakeEmbedder(), api_key=API_KEY)
        with helpers.serving(app=app) as url:
            client = HttpProbeClient(base_url=url, api_key=API_KEY)
            response = client.get(path=protocol.DESCRIBE_PATH, timeout=TIMEOUT)

        assert response.status_code == 200

    def test_get__status_the_server_chose(self) -> None:
        """A status is an answer that the checks read, never an exception."""
        app = server.create_app(embedder=FakeEmbedder(), api_key=API_KEY)
        with helpers.serving(app=app) as url:
            response = HttpProbeClient(base_url=url).get(
                path=protocol.DESCRIBE_PATH, timeout=TIMEOUT
            )

        assert response.status_code == 401
        assert b"bearer token" in response.body

    def test_get__redirect(self) -> None:
        """Following one would send the bearer token to an address nobody typed."""
        with helpers.serving(app=_redirecting_app()) as url:
            response = HttpProbeClient(base_url=url, api_key=API_KEY).get(
                path=protocol.DESCRIBE_PATH, timeout=TIMEOUT
            )

        assert response.status_code == 307

    def test_get__server_that_is_not_there(self) -> None:
        client = HttpProbeClient(base_url="http://127.0.0.1:1")

        with pytest.raises(ConformanceRequestError, match="got no answer"):
            client.get(path=protocol.DESCRIBE_PATH, timeout=TIMEOUT)

    def test_get__address_that_urllib_cannot_read(self) -> None:
        """A mistyped address fails here, not at construction, and is no traceback either."""
        client = HttpProbeClient(base_url="http://127.0.0.1:notaport")

        with pytest.raises(ConformanceRequestError, match="got no answer"):
            client.get(path=protocol.DESCRIBE_PATH, timeout=TIMEOUT)

    def test_get__api_key_that_is_empty(self) -> None:
        """An unset variable in a shell reads as empty, and means no key at all."""
        app = server.create_app(embedder=FakeEmbedder())
        with helpers.serving(app=app) as url:
            response = HttpProbeClient(base_url=url, api_key="").get(
                path=protocol.DESCRIBE_PATH, timeout=TIMEOUT
            )

        assert response.status_code == 200

    def test_get__body_over_the_limit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(client_module, "MAX_RESPONSE_BYTES", 8)
        with helpers.serving(app=_long_body_app()) as url:
            client = HttpProbeClient(base_url=url)

            with pytest.raises(ConformanceRequestError, match="answers over 8 bytes"):
                client.get(path=protocol.DESCRIBE_PATH, timeout=TIMEOUT)


def _redirecting_app() -> FastAPI:
    app = FastAPI()

    @app.get(protocol.DESCRIBE_PATH)
    def describe_route() -> RedirectResponse:
        return RedirectResponse(url="http://169.254.169.254/latest/meta-data/")

    return app


def _long_body_app() -> FastAPI:
    app = FastAPI()

    @app.get(protocol.DESCRIBE_PATH)
    def describe_route() -> PlainTextResponse:
        return PlainTextResponse("x" * 64)

    return app
