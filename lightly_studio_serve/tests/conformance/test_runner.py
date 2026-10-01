from __future__ import annotations

from typing import Any

import pytest

from lightly_studio_serve.conformance import runner
from lightly_studio_serve.conformance.client import ConformanceRequestError, ProbeResponse
from lightly_studio_serve.conformance.report import ConformanceReport, Outcome
from lightly_studio_serve.embedder import Capability
from lightly_studio_serve.server import create_app
from tests.conformance import helpers
from tests.conformance.helpers import AppProbeClient, FakeEmbedder, FakeTextEmbedder

API_KEY = "the-key"


class UnreachableProbeClient:
    """Answers every request the way a client answers a host that is not there."""

    def get(self, path: str, timeout: float) -> ProbeResponse:
        raise ConformanceRequestError(f"{path} reached no server: connection refused.")

    def post(self, path: str, content_type: str, body: bytes, timeout: float) -> ProbeResponse:
        raise ConformanceRequestError(f"{path} reached no server: connection refused.")


def test_check_conformance__against_serve() -> None:
    """The server of this package passes its own kit. This is the check CI runs."""
    client = AppProbeClient(app=create_app(embedder=FakeEmbedder()))

    report = runner.check_conformance(client=client)

    assert report.passed
    assert _outcomes(report=report) == {
        Capability.TEXT: Outcome.PASSED,
        Capability.IMAGE_BYTES: Outcome.PASSED,
        Capability.VIDEO_BYTES: Outcome.PASSED,
    }


def test_check_conformance__text_only_model() -> None:
    """A model that embeds no video reads as not advertised, never as a failure."""
    client = AppProbeClient(app=create_app(embedder=FakeTextEmbedder()))

    report = runner.check_conformance(client=client)

    assert report.passed
    assert _outcomes(report=report) == {
        Capability.TEXT: Outcome.PASSED,
        Capability.IMAGE_BYTES: Outcome.NOT_ADVERTISED,
        Capability.VIDEO_BYTES: Outcome.NOT_ADVERTISED,
    }


def test_check_conformance__model_still_loading() -> None:
    client = AppProbeClient(app=create_app(embedder=FakeEmbedder(ready=False)))

    report = runner.check_conformance(client=client)

    assert not report.passed
    assert _outcomes(report=report)[Capability.TEXT] is Outcome.NOT_READY


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
    """The bodies may follow another contract, so the run says so and probes anyway."""
    app = helpers.canned_app(
        describe=helpers.describe_body(protocol_version="2.0"),
        embeddings=helpers.embeddings_body(),
    )

    report = runner.check_conformance(client=AppProbeClient(app=app))

    assert not report.passed
    assert report.describe_problems == (
        "/v1/describe answers protocol_version '2.0'. This kit tests '1.0'.",
    )
    assert _outcomes(report=report)[Capability.TEXT] is Outcome.PASSED


def test_check_conformance__advertised_capability_with_no_route() -> None:
    client = AppProbeClient(app=helpers.canned_app(describe=helpers.describe_body()))

    report = runner.check_conformance(client=client)

    assert not report.passed
    assert _details(report=report, capability=Capability.TEXT) == (
        '/v1/embed/texts answers 404, expected 200. {"detail":"Not Found"}',
    )


# Every case carries the describe body whose values its line quotes, so the line reads alone.
@pytest.mark.parametrize(
    ("describe", "embeddings", "detail"),
    [
        pytest.param(
            helpers.describe_body(dimension=2),
            helpers.embeddings_body(dimension=2, embeddings=[[0.5, -0.5, 0.25]]),
            "/v1/embed/texts answers a body that the protocol does not allow: "
            "Value error, Embedding 0 has 3 values. The server declares dimension 2.",
            id="a row wider than the body declares",
        ),
        pytest.param(
            helpers.describe_body(dimension=2),
            helpers.embeddings_body(dimension=3, embeddings=[[1.0, 1.0, 1.0]]),
            "/v1/embed/texts answers dimension 3, /v1/describe answers 2. LightlyStudio stores "
            "vectors of the dimension that the server describes.",
            id="a dimension that /v1/describe does not report",
        ),
        pytest.param(
            helpers.describe_body(),
            {"space_key": helpers.SPACE_KEY, "dimension": 2, "embeddings": [[0.5, -0.5]]},
            "/v1/embed/texts answers a body that the protocol does not allow: "
            "kept_indices: Field required",
            id="no kept_indices",
        ),
        pytest.param(
            helpers.describe_body(),
            helpers.embeddings_body(embeddings=[[0.5, float("nan")]]),
            "/v1/embed/texts answers a body that the protocol does not allow: "
            "Value error, Embedding 0 holds a value that is not finite.",
            id="a value that is not finite",
        ),
        pytest.param(
            helpers.describe_body(space_key="acme/model@v1"),
            helpers.embeddings_body(space_key="acme/model@v2"),
            "/v1/embed/texts answers space_key 'acme/model@v2', /v1/describe answers "
            "'acme/model@v1'. Every response repeats the space that the server describes.",
            id="a space_key that /v1/describe does not report",
        ),
        pytest.param(
            helpers.describe_body(),
            helpers.embeddings_body(kept_indices=[], embeddings=[]),
            "/v1/embed/texts answers kept_indices [], expected [0]. The probe carries one item "
            "that the format allows, so a server that reads the format keeps it.",
            id="none of the probe items kept",
        ),
    ],
)
def test_check_conformance__server_that_breaks_the_protocol(
    describe: dict[str, Any], embeddings: dict[str, Any], detail: str
) -> None:
    app = helpers.canned_app(describe=describe, embeddings=embeddings)

    report = runner.check_conformance(client=AppProbeClient(app=app))

    assert not report.passed
    assert _details(report=report, capability=Capability.TEXT) == (detail,)


def _outcomes(report: ConformanceReport) -> dict[Capability, Outcome]:
    return {entry.capability: entry.outcome for entry in report.capabilities}


def _details(report: ConformanceReport, capability: Capability) -> tuple[str, ...]:
    return next(entry.details for entry in report.capabilities if entry.capability is capability)
