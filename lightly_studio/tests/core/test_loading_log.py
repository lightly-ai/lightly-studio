"""Unit tests for the per-run file-outcome report."""

from __future__ import annotations

import logging

import pytest

from lightly_studio.core import loading_log
from lightly_studio.core.loading_log import (
    AllInputFilesFailedError,
    FileOutcome,
    FileOutcomeReport,
)


class TestRecordOutcomes:
    def test_record_each_outcome_counts_and_keeps_examples(self) -> None:
        report = FileOutcomeReport()

        report.record("added.jpg", FileOutcome.ADDED)
        report.record("present.jpg", FileOutcome.ALREADY_PRESENT)
        report.record("missing.jpg", FileOutcome.MISSING)
        report.record("broken.jpg", FileOutcome.BROKEN)

        assert report.counts[FileOutcome.ADDED] == 1
        assert report.counts[FileOutcome.ALREADY_PRESENT] == 1
        assert report.counts[FileOutcome.MISSING] == 1
        assert report.counts[FileOutcome.BROKEN] == 1
        assert report.example_paths[FileOutcome.ADDED] == ["added.jpg"]
        assert report.example_paths[FileOutcome.MISSING] == ["missing.jpg"]

    def test_record_many_records_every_path(self) -> None:
        report = FileOutcomeReport()

        report.record_many(["a.jpg", "b.jpg", "c.jpg"], FileOutcome.ALREADY_PRESENT)

        assert report.counts[FileOutcome.ALREADY_PRESENT] == 3
        assert report.example_paths[FileOutcome.ALREADY_PRESENT] == ["a.jpg", "b.jpg", "c.jpg"]

    def test_example_paths_are_capped(self) -> None:
        report = FileOutcomeReport()

        report.record_many(
            [f"file_{i}.jpg" for i in range(loading_log.MAX_EXAMPLE_PATHS_TO_SHOW + 3)],
            FileOutcome.BROKEN,
        )

        # Every file is counted, but only a few examples are kept.
        assert report.counts[FileOutcome.BROKEN] == loading_log.MAX_EXAMPLE_PATHS_TO_SHOW + 3
        assert (
            len(report.example_paths[FileOutcome.BROKEN]) == loading_log.MAX_EXAMPLE_PATHS_TO_SHOW
        )


class TestRaiseIfAllFailed:
    def test_raises_when_zero_succeeded_of_n_attempted(self) -> None:
        report = FileOutcomeReport()
        report.record_many(["a.jpg", "b.jpg"], FileOutcome.MISSING)
        report.record("c.jpg", FileOutcome.BROKEN)

        with pytest.raises(AllInputFilesFailedError):
            report.raise_if_all_failed()

    def test_does_not_raise_when_at_least_one_added(self) -> None:
        report = FileOutcomeReport()
        report.record("ok.jpg", FileOutcome.ADDED)
        report.record("bad.jpg", FileOutcome.BROKEN)

        report.raise_if_all_failed()  # Must not raise.

    def test_does_not_raise_when_zero_attempted_all_already_present(self) -> None:
        report = FileOutcomeReport()
        report.record_many(["a.jpg", "b.jpg"], FileOutcome.ALREADY_PRESENT)

        report.raise_if_all_failed()  # Must not raise: already-present is not an attempt.

    def test_does_not_raise_when_nothing_recorded(self) -> None:
        report = FileOutcomeReport()

        report.raise_if_all_failed()  # Must not raise.


class TestLogSummary:
    def test_summary_logs_counts_per_outcome(self, caplog: pytest.LogCaptureFixture) -> None:
        report = FileOutcomeReport()
        report.record("a.jpg", FileOutcome.ADDED)
        report.record_many(["b.jpg", "c.jpg"], FileOutcome.ALREADY_PRESENT)
        report.record("d.jpg", FileOutcome.MISSING)
        report.record("e.jpg", FileOutcome.BROKEN)

        caplog.set_level(logging.INFO, logger="lightly_studio.core.loading_log")
        report.log_summary()

        log_text = caplog.text
        assert "1 added" in log_text
        assert "2 already-present" in log_text
        assert "1 missing" in log_text
        assert "1 broken" in log_text

    def test_summary_logs_example_paths_for_problem_outcomes(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        report = FileOutcomeReport()
        report.record("missing.jpg", FileOutcome.MISSING)
        report.record("broken.jpg", FileOutcome.BROKEN)
        report.record("present.jpg", FileOutcome.ALREADY_PRESENT)

        caplog.set_level(logging.INFO, logger="lightly_studio.core.loading_log")
        report.log_summary()

        log_text = caplog.text
        assert "missing.jpg" in log_text
        assert "broken.jpg" in log_text
        assert "present.jpg" in log_text
