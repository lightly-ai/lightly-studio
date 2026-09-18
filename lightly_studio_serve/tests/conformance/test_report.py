from __future__ import annotations

from collections.abc import Sequence

import pytest

from lightly_studio_serve.conformance.report import (
    CapabilityReport,
    ConformanceReport,
    Outcome,
    render,
)
from lightly_studio_serve.embedder import Capability
from lightly_studio_serve.protocol import DescribeResponse, ServerLimits

DESCRIBED = DescribeResponse(
    protocol_version="1.0",
    space_key="acme/model@v1",
    dimension=2,
    ready=True,
    capabilities=[Capability.TEXT],
    limits=ServerLimits(),
)


class TestConformanceReport:
    @pytest.mark.parametrize(
        ("outcomes", "passed"),
        [
            ([Outcome.PASSED], True),
            # A model that embeds no video is not a model that fails on video.
            ([Outcome.PASSED, Outcome.NOT_ADVERTISED], True),
            ([Outcome.PASSED, Outcome.FAILED], False),
            # Nothing was probed, so the run answers for nothing.
            ([Outcome.NOT_READY], False),
        ],
    )
    def test_passed(self, outcomes: Sequence[Outcome], passed: bool) -> None:
        report = ConformanceReport(
            described=DESCRIBED,
            capabilities=tuple(
                CapabilityReport(capability=Capability.TEXT, outcome=outcome)
                for outcome in outcomes
            ),
        )

        assert report.passed is passed

    def test_passed__broken_describe(self) -> None:
        report = ConformanceReport(described=None, describe_problems=("Connection refused.",))

        assert not report.passed


def test_render() -> None:
    report = ConformanceReport(
        described=DESCRIBED,
        capabilities=(
            CapabilityReport(capability=Capability.TEXT, outcome=Outcome.PASSED),
            CapabilityReport(
                capability=Capability.IMAGE_BYTES,
                outcome=Outcome.FAILED,
                details=("It answers dimension 3.",),
            ),
            CapabilityReport(capability=Capability.VIDEO_BYTES, outcome=Outcome.NOT_ADVERTISED),
        ),
    )

    assert render(report=report) == (
        "protocol 1.0\n"
        "space    acme/model@v1\n"
        "vectors  2 values\n"
        "ready    yes\n"
        "\n"
        "text         passed\n"
        "image_bytes  failed\n"
        "      It answers dimension 3.\n"
        "video_bytes  not advertised"
    )


def test_render__unreachable_server() -> None:
    report = ConformanceReport(described=None, describe_problems=("Connection refused.",))

    assert render(report=report) == "Connection refused."
