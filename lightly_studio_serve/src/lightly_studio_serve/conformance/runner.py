"""Runs the protocol probes against one server and says what each capability did.

``/v1/describe`` always runs. Each advertised capability then costs one round trip. The
kit probes the capabilities that cross a wire, so a path capability gets no line.
"""

from __future__ import annotations

from http import HTTPStatus
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from lightly_studio_serve import protocol, validation
from lightly_studio_serve.conformance import probes
from lightly_studio_serve.conformance.client import (
    ConformanceRequestError,
    ProbeClient,
    ProbeResponse,
)
from lightly_studio_serve.conformance.probes import Probe
from lightly_studio_serve.conformance.report import CapabilityReport, ConformanceReport, Outcome
from lightly_studio_serve.embedder import Capability
from lightly_studio_serve.protocol import DescribeResponse, EmbeddingsResponse

DESCRIBE_TIMEOUT_SECONDS = 5.0
"""How long ``/v1/describe`` may take. A person waits for this call, so it stays short."""

PROBE_TIMEOUT_SECONDS = 60.0
"""How long one probe may take. A cold model on a CPU takes far longer than a warm one."""

# How much of an unexpected answer a problem repeats.
_BODY_EXCERPT_CHARS = 200

_Body = TypeVar("_Body", bound=BaseModel)


class _FaultError(Exception):
    """An answer the checks cannot use, worded the way the report prints it."""


def check_conformance(
    client: ProbeClient,
    describe_timeout: float = DESCRIBE_TIMEOUT_SECONDS,
    probe_timeout: float = PROBE_TIMEOUT_SECONDS,
) -> ConformanceReport:
    """Probe every capability a server advertises and report each one on its own.

    Args:
        client: Sends the requests to the server under test.
        describe_timeout: The seconds ``/v1/describe`` may take.
        probe_timeout: The seconds one probe may take.

    Returns:
        What the run found. ``ConformanceReport.passed`` is the verdict.
    """
    try:
        described = _describe(client=client, timeout=describe_timeout)
    # No answer, or one the checks cannot use. Either way, no capability can be probed.
    except (ConformanceRequestError, _FaultError) as error:
        return ConformanceReport(described=None, describe_problems=(str(error),))
    return ConformanceReport(
        described=described,
        describe_problems=_version_problems(described=described),
        capabilities=tuple(
            _check_capability(
                client=client, described=described, capability=capability, timeout=probe_timeout
            )
            for capability in probes.PROBES
        ),
    )


def _describe(client: ProbeClient, timeout: float) -> DescribeResponse:
    """Read ``/v1/describe``, the one endpoint that every server has."""
    response = client.get(path=protocol.DESCRIBE_PATH, timeout=timeout)
    return _parsed(model=DescribeResponse, response=response, path=protocol.DESCRIBE_PATH)


def _version_problems(described: DescribeResponse) -> tuple[str, ...]:
    """Name a major version this kit does not test. The probes run anyway."""
    if _major(version=described.protocol_version) == _major(version=protocol.PROTOCOL_VERSION):
        return ()
    return (
        f"{protocol.DESCRIBE_PATH} answers protocol_version "
        f"{described.protocol_version!r}. This kit tests {protocol.PROTOCOL_VERSION!r}.",
    )


def _major(version: str) -> str:
    return version.partition(".")[0]


def _check_capability(
    client: ProbeClient, described: DescribeResponse, capability: Capability, timeout: float
) -> CapabilityReport:
    """Report one capability. Only an advertised one of a loaded model is probed."""
    if capability not in described.capabilities:
        return CapabilityReport(capability=capability, outcome=Outcome.NOT_ADVERTISED)
    if not described.ready:
        return CapabilityReport(capability=capability, outcome=Outcome.NOT_READY)
    problems = _run_probe(client=client, probe=probes.PROBES[capability], timeout=timeout)
    outcome = Outcome.FAILED if problems else Outcome.PASSED
    return CapabilityReport(capability=capability, outcome=outcome, details=tuple(problems))


def _run_probe(client: ProbeClient, probe: Probe, timeout: float) -> list[str]:
    """Send one probe and read its answer as the protocol defines it."""
    try:
        response = client.post(
            path=probe.path, content_type=probe.content_type, body=probe.body, timeout=timeout
        )
        _parsed(model=EmbeddingsResponse, response=response, path=probe.path)
    except (ConformanceRequestError, _FaultError) as error:
        return [str(error)]
    return []


def _parsed(model: type[_Body], response: ProbeResponse, path: str) -> _Body:
    """Read one body of the protocol, or raise a fault naming the rule it breaks."""
    if response.status_code != HTTPStatus.OK:
        raise _FaultError(
            f"{path} answers {response.status_code}, expected {int(HTTPStatus.OK)}. "
            f"{_excerpt(body=response.body)}"
        )
    try:
        return model.model_validate_json(response.body)
    except ValidationError as error:
        raise _FaultError(
            f"{path} answers a body that the protocol does not allow: "
            f"{validation.name_broken_rules(error=error)}"
        ) from error


def _excerpt(body: bytes) -> str:
    """Show the start of a body, so a person sees what the server sent."""
    text = body.decode("utf-8", errors="replace").strip()
    if not text:
        return "The body is empty."
    if len(text) > _BODY_EXCERPT_CHARS:
        return f"{text[:_BODY_EXCERPT_CHARS]}..."
    return text
