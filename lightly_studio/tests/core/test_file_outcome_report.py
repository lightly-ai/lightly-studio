from __future__ import annotations

import logging

import pytest

from lightly_studio.core.file_outcome_report import (
    MAX_EXAMPLE_PATHS_PER_OUTCOME,
    FileOutcome,
    FileOutcomeReport,
)
from lightly_studio.errors import AllInputFilesFailedError


class TestFileOutcomeReport:
    def test_process_file__added(self) -> None:
        report = FileOutcomeReport()

        outcome = report.process_file(path="a.jpg", operation=lambda: FileOutcome.ADDED)

        assert outcome == FileOutcome.ADDED
        assert report.counts[FileOutcome.ADDED] == 1
        assert report.example_paths[FileOutcome.ADDED] == ["a.jpg"]

    def test_process_file__already_present(self) -> None:
        report = FileOutcomeReport()

        outcome = report.process_file(path="a.jpg", operation=lambda: FileOutcome.ALREADY_PRESENT)

        assert outcome == FileOutcome.ALREADY_PRESENT
        assert report.counts[FileOutcome.ALREADY_PRESENT] == 1

    def test_process_file__missing(self) -> None:
        report = FileOutcomeReport()

        def operation() -> FileOutcome:
            raise FileNotFoundError("a.jpg")

        outcome = report.process_file(path="a.jpg", operation=operation)

        assert outcome is None
        assert report.counts[FileOutcome.MISSING] == 1
        assert report.example_paths[FileOutcome.MISSING] == ["a.jpg"]

    def test_process_file__broken(self) -> None:
        report = FileOutcomeReport()

        def operation() -> FileOutcome:
            raise ValueError("cannot decode image")

        outcome = report.process_file(path="a.jpg", operation=operation)

        assert outcome is None
        assert report.counts[FileOutcome.BROKEN] == 1
        assert report.example_paths[FileOutcome.BROKEN] == ["a.jpg"]

    def test_process_file__tolerates_failure_without_placeholder(self) -> None:
        # A bad item is recorded and skipped; no other outcome row is created.
        report = FileOutcomeReport()

        report.process_file(path="bad.jpg", operation=lambda: (_ for _ in ()).throw(OSError()))

        assert report.counts[FileOutcome.ADDED] == 0
        assert report.counts[FileOutcome.ALREADY_PRESENT] == 0
        assert report.counts[FileOutcome.MISSING] == 0
        assert report.counts[FileOutcome.BROKEN] == 1

    def test_record__caps_example_paths(self) -> None:
        report = FileOutcomeReport()
        n_paths = MAX_EXAMPLE_PATHS_PER_OUTCOME + 3

        for i in range(n_paths):
            report.record(path=f"{i}.jpg", outcome=FileOutcome.MISSING)

        assert report.counts[FileOutcome.MISSING] == n_paths
        assert len(report.example_paths[FileOutcome.MISSING]) == MAX_EXAMPLE_PATHS_PER_OUTCOME

    def test_n_attempted__excludes_already_present(self) -> None:
        report = FileOutcomeReport()
        report.record(path="a.jpg", outcome=FileOutcome.ADDED)
        report.record(path="b.jpg", outcome=FileOutcome.MISSING)
        report.record(path="c.jpg", outcome=FileOutcome.BROKEN)
        report.record(path="d.jpg", outcome=FileOutcome.ALREADY_PRESENT)

        assert report.n_attempted == 3
        assert report.n_succeeded == 1

    def test_raise_if_all_failed__raises_when_all_attempts_fail(self) -> None:
        report = FileOutcomeReport()
        report.record(path="a.jpg", outcome=FileOutcome.MISSING)
        report.record(path="b.jpg", outcome=FileOutcome.BROKEN)

        with pytest.raises(AllInputFilesFailedError):
            report.raise_if_all_failed()

    def test_raise_if_all_failed__no_raise_when_some_added(self) -> None:
        report = FileOutcomeReport()
        report.record(path="a.jpg", outcome=FileOutcome.ADDED)
        report.record(path="b.jpg", outcome=FileOutcome.MISSING)

        report.raise_if_all_failed()  # Does not raise.

    def test_raise_if_all_failed__no_raise_when_all_already_present(self) -> None:
        # 0 attempted because everything was already present must not raise.
        report = FileOutcomeReport()
        report.record(path="a.jpg", outcome=FileOutcome.ALREADY_PRESENT)
        report.record(path="b.jpg", outcome=FileOutcome.ALREADY_PRESENT)

        report.raise_if_all_failed()  # Does not raise.

    def test_raise_if_all_failed__no_raise_when_nothing_recorded(self) -> None:
        report = FileOutcomeReport()

        report.raise_if_all_failed()  # Does not raise.

    def test_log_summary(self, caplog: pytest.LogCaptureFixture) -> None:
        caplog.set_level(logging.INFO, logger="lightly_studio.core.file_outcome_report")
        report = FileOutcomeReport()
        report.record(path="a.jpg", outcome=FileOutcome.ADDED)
        report.record(path="b.jpg", outcome=FileOutcome.MISSING)

        report.log_summary()

        log_text = caplog.text
        assert "added: 1" in log_text
        assert "missing: 1" in log_text
        assert "Example added paths: a.jpg" in log_text
        assert "Example missing paths: b.jpg" in log_text
