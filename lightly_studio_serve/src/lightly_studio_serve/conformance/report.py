"""What a conformance run found, per capability, and how it reads on a terminal."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from lightly_studio_serve.embedder import Capability
from lightly_studio_serve.protocol import DescribeResponse

# The indent of a detail under its capability.
_DETAIL_INDENT = " " * 6


class Outcome(str, Enum):
    """What a run can say about one capability."""

    PASSED = "passed"
    FAILED = "failed"

    NOT_ADVERTISED = "not advertised"
    """``/v1/describe`` does not list the capability. This is not a fault."""

    NOT_READY = "not ready"
    """The model was still loading, so the run sent no probe."""


# A run that probed nothing answers for nothing.
_UNPASSED = frozenset({Outcome.FAILED, Outcome.NOT_READY})


@dataclass(frozen=True)
class CapabilityReport:
    """What one capability of one server did."""

    capability: Capability
    outcome: Outcome

    details: tuple[str, ...] = ()
    """The reasons behind ``outcome``. Empty for a capability that passed."""


@dataclass(frozen=True)
class ConformanceReport:
    """What a run found on one server."""

    described: DescribeResponse | None
    """What ``/v1/describe`` answered, or ``None`` if the run could not read it."""

    describe_problems: tuple[str, ...] = ()
    """The faults of ``/v1/describe`` itself."""

    capabilities: tuple[CapabilityReport, ...] = ()
    """One entry per capability the kit probes."""

    @property
    def passed(self) -> bool:
        """Whether the server implements the protocol as far as this run can tell.

        A capability the server does not advertise leaves the answer ``True``.
        """
        return (
            self.described is not None
            and not self.describe_problems
            and not any(capability.outcome in _UNPASSED for capability in self.capabilities)
        )


def render(report: ConformanceReport) -> str:
    """Write a report as the lines a person reads, without a trailing newline.

    Args:
        report: What a run found.

    Returns:
        The report as text.
    """
    lines = _identity_lines(report=report)
    lines.extend(report.describe_problems)
    if report.capabilities:
        lines.append("")
        lines.extend(_capability_lines(report=report))
    return "\n".join(lines)


def _identity_lines(report: ConformanceReport) -> list[str]:
    """Name what the server says it is."""
    described = report.described
    if described is None:
        return []
    return [
        f"protocol {described.protocol_version}",
        f"space    {described.space_key}",
        f"vectors  {described.dimension} values",
        f"ready    {'yes' if described.ready else 'no, the model is still loading'}",
    ]


def _capability_lines(report: ConformanceReport) -> list[str]:
    """One line per capability, with the details of a failure under it."""
    width = max(len(entry.capability.value) for entry in report.capabilities)
    lines = []
    for entry in report.capabilities:
        lines.append(f"{entry.capability.value:<{width}}  {entry.outcome.value}")
        lines.extend(f"{_DETAIL_INDENT}{detail}" for detail in entry.details)
    return lines
