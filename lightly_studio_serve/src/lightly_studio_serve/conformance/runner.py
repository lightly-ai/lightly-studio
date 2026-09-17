"""Runs the protocol checks against one server and says what it answered.

``/v1/describe`` always runs. It is the one endpoint every server has, and it already
catches an unreachable host, a bad key and a server that is not the one the person meant.
"""

from __future__ import annotations

from lightly_studio_serve import protocol
from lightly_studio_serve.conformance.client import ConformanceRequestError, ProbeClient
from lightly_studio_serve.conformance.report import ConformanceReport
from lightly_studio_serve.protocol import DescribeResponse

DESCRIBE_TIMEOUT_SECONDS = 5.0
"""How long ``/v1/describe`` may take. A person waits for this call, so it stays short."""


def check_conformance(
    client: ProbeClient, describe_timeout: float = DESCRIBE_TIMEOUT_SECONDS
) -> ConformanceReport:
    """Read what a server says it is, and report a server that answers nothing.

    Args:
        client: Sends the requests to the server under test.
        describe_timeout: The seconds ``/v1/describe`` may take.

    Returns:
        What the run found. ``ConformanceReport.passed`` is the verdict.
    """
    try:
        described = _describe(client=client, timeout=describe_timeout)
    except ConformanceRequestError as error:
        return ConformanceReport(described=None, describe_problems=(str(error),))
    return ConformanceReport(described=described)


def _describe(client: ProbeClient, timeout: float) -> DescribeResponse:
    """Read ``/v1/describe``, the one endpoint that every server has."""
    response = client.get(path=protocol.DESCRIBE_PATH, timeout=timeout)
    return DescribeResponse.model_validate_json(response.body)
