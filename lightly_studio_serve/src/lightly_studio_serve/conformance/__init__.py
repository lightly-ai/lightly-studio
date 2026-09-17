"""Checks that a server implements the LightlyStudio embedding protocol.

The kit runs against ``serve`` from this package and against a customer's implementation
in any language, and needs no dataset and no LightlyStudio install. LightlyStudio runs the
same checks behind its **Check connection** button.
"""

from lightly_studio_serve.conformance.client import (
    ConformanceRequestError,
    HttpProbeClient,
    ProbeClient,
    ProbeResponse,
)
from lightly_studio_serve.conformance.report import (
    CapabilityReport,
    ConformanceReport,
    Outcome,
    render,
)
from lightly_studio_serve.conformance.runner import check_conformance

__all__ = [
    "CapabilityReport",
    "ConformanceReport",
    "ConformanceRequestError",
    "HttpProbeClient",
    "Outcome",
    "ProbeClient",
    "ProbeResponse",
    "check_conformance",
    "render",
]
