from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse, RedirectResponse

from lightly_studio_serve import protocol
from lightly_studio_serve.conformance import client as client_module
from lightly_studio_serve.conformance.client import ConformanceRequestError, HttpProbeClient
from lightly_studio_serve.conformance.probes import PROBES
from lightly_studio_serve.embedder import Capability
from lightly_studio_serve.server import create_app
from tests.conformance import helpers
from tests.conformance.helpers import FakeEmbedder

API_KEY = "the-key"
TIMEOUT = 5.0


class TestHttpProbeClient:
    def test_init__address_that_is_no_http_url(self) -> None:
        """The opener answers nothing at all for another scheme, so this must not pass."""
        with pytest.raises(ValueError, match="must start with http"):
            HttpProbeClient(base_url="127.0.0.1:8080")

    def test_get(self) -> None:
        with helpers.serving(app=create_app(embedder=FakeEmbedder())) as url:
            response = HttpProbeClient(base_url=f"{url}/").get(
                path=protocol.DESCRIBE_PATH, timeout=TIMEOUT
            )

        assert response.status_code == 200
        assert b'"space_key"' in response.body

    def test_post(self) -> None:
        probe = PROBES[Capability.IMAGE_BYTES]
        with helpers.serving(app=create_app(embedder=FakeEmbedder())) as url:
            response = HttpProbeClient(base_url=url).post(
                path=probe.path, content_type=probe.content_type, body=probe.body, timeout=TIMEOUT
            )

        assert response.status_code == 200
        assert b'"kept_indices":[0]' in response.body

    def test_get__api_key(self) -> None:
        app = create_app(embedder=FakeEmbedder(), api_key=API_KEY)
        with helpers.serving(app=app) as url:
            client = HttpProbeClient(base_url=url, api_key=API_KEY)
            response = client.get(path=protocol.DESCRIBE_PATH, timeout=TIMEOUT)

        assert response.status_code == 200

    def test_get__status_the_server_chose(self) -> None:
        """A status is an answer that the checks read, never an exception."""
        app = create_app(embedder=FakeEmbedder(), api_key=API_KEY)
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
