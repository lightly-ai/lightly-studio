from __future__ import annotations

from lightly_studio_serve.conformance import runner
from lightly_studio_serve.conformance.client import ConformanceRequestError, ProbeResponse
from lightly_studio_serve.server import create_app
from tests.conformance import helpers
from tests.conformance.helpers import DIMENSION, SPACE_KEY, AppProbeClient, FakeEmbedder

API_KEY = "the-key"


class UnreachableProbeClient:
    """Answers every request the way a client answers a host that is not there."""

    def get(self, path: str, timeout: float) -> ProbeResponse:
        raise ConformanceRequestError(f"{path} reached no server: connection refused.")

    def post(self, path: str, content_type: str, body: bytes, timeout: float) -> ProbeResponse:
        raise ConformanceRequestError(f"{path} reached no server: connection refused.")


def test_check_conformance__against_serve() -> None:
    """The server of this package answers its own kit. This is the check CI runs."""
    client = AppProbeClient(app=create_app(embedder=FakeEmbedder()))

    report = runner.check_conformance(client=client)

    assert report.passed
    assert report.described is not None
    assert report.described.space_key == SPACE_KEY
    assert report.described.dimension == DIMENSION
    assert report.described.ready


def test_check_conformance__unreachable_server() -> None:
    report = runner.check_conformance(client=UnreachableProbeClient())

    assert not report.passed
    assert report.described is None
    assert report.describe_problems == ("/v1/describe reached no server: connection refused.",)


def test_check_conformance__missing_key() -> None:
    """A run without the key of the server stops at /v1/describe, with the answer shown."""
    client = AppProbeClient(app=create_app(embedder=FakeEmbedder(), api_key=API_KEY))

    report = runner.check_conformance(client=client)

    assert not report.passed
    assert report.describe_problems == (
        '/v1/describe answers 401, expected 200. {"detail":"Missing or invalid bearer token."}',
    )


def test_check_conformance__describe_that_breaks_the_protocol() -> None:
    client = AppProbeClient(app=helpers.canned_app(describe=helpers.describe_body(dimension=0)))

    report = runner.check_conformance(client=client)

    assert not report.passed
    assert report.describe_problems == (
        "/v1/describe answers a body that the protocol does not allow: "
        "dimension: Input should be greater than 0",
    )


def test_check_conformance__another_protocol_version() -> None:
    """The bodies may follow another contract, so the run says so and reads on."""
    app = helpers.canned_app(describe=helpers.describe_body(protocol_version="2.0"))

    report = runner.check_conformance(client=AppProbeClient(app=app))

    assert not report.passed
    assert report.describe_problems == (
        "/v1/describe answers protocol_version '2.0'. This kit tests '1.0'.",
    )
