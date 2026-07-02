"""Tests for the central file-outcome report helper."""

from __future__ import annotations

import logging

import pytest

from lightly_studio.core.file_outcome_report import (
    AllInputFilesFailedError,
    AlreadyPresentInputFileError,
    BrokenInputFileError,
    FileOutcome,
    FileOutcomeReport,
    MissingInputFileError,
)


class TestFileOutcomeReport:
    def test_record(self) -> None:
        report = FileOutcomeReport()
        report.record(path="a.jpg", outcome=FileOutcome.ADDED)
        report.record(path="b.jpg", outcome=FileOutcome.ADDED)
        report.record(path="c.jpg", outcome=FileOutcome.MISSING)

        assert report._counts[FileOutcome.ADDED] == 2
        assert report._counts[FileOutcome.MISSING] == 1
        assert report._example_paths[FileOutcome.ADDED] == ["a.jpg", "b.jpg"]
        assert report._example_paths[FileOutcome.MISSING] == ["c.jpg"]

    def test_record__example_path_cap(self) -> None:
        report = FileOutcomeReport(max_examples_per_outcome=2)
        for index in range(3):
            report.record(path=f"{index}.jpg", outcome=FileOutcome.BROKEN)

        assert report._counts[FileOutcome.BROKEN] == 3
        assert report._example_paths[FileOutcome.BROKEN] == ["0.jpg", "1.jpg"]

    def test_track__records_added_on_clean_exit(self) -> None:
        report = FileOutcomeReport()
        with report.track("a.jpg"):
            pass

        assert report._counts[FileOutcome.ADDED] == 1
        assert report._example_paths[FileOutcome.ADDED] == ["a.jpg"]

    def test_track__records_already_present(self) -> None:
        report = FileOutcomeReport()
        with report.track("a.jpg"):
            raise AlreadyPresentInputFileError("Some error message")

        assert report._counts[FileOutcome.ALREADY_PRESENT] == 1
        assert report._counts[FileOutcome.ADDED] == 0

    def test_track__records_missing(self) -> None:
        report = FileOutcomeReport()
        with report.track("a.jpg"):
            raise MissingInputFileError("Some error message")

        assert report._counts[FileOutcome.MISSING] == 1
        assert report._example_paths[FileOutcome.MISSING] == ["a.jpg"]

    def test_track__records_broken(self) -> None:
        report = FileOutcomeReport()
        with report.track("a.jpg"):
            raise BrokenInputFileError("Some error message")

        assert report._counts[FileOutcome.BROKEN] == 1
        assert report._example_paths[FileOutcome.BROKEN] == ["a.jpg"]

    def test_track__propagates_non_input_exception(self) -> None:
        report = FileOutcomeReport()
        with pytest.raises(ValueError, match="boom"), report.track("a.jpg"):
            raise ValueError("boom")

        # Nothing recorded: the exception is a bug, not a file outcome.
        assert all(count == 0 for count in report._counts.values())

    def test_track__loop_continues_after_tolerated_errors(self) -> None:
        report = FileOutcomeReport()
        paths = ["good.jpg", "missing.jpg", "broken.jpg", "good2.jpg"]
        for path in paths:
            with report.track(path):
                if path == "missing.jpg":
                    raise MissingInputFileError(path)
                if path == "broken.jpg":
                    raise BrokenInputFileError(path)

        assert report._counts[FileOutcome.ADDED] == 2
        assert report._counts[FileOutcome.MISSING] == 1
        assert report._counts[FileOutcome.BROKEN] == 1

    def test_raise_if_all_failed__raises_when_all_failed(self) -> None:
        report = FileOutcomeReport()
        report.record(path="a.jpg", outcome=FileOutcome.MISSING)
        report.record(path="b.jpg", outcome=FileOutcome.BROKEN)

        with pytest.raises(AllInputFilesFailedError):
            report.raise_if_all_failed()

    def test_raise_if_all_failed__no_raise_when_some_added(self) -> None:
        report = FileOutcomeReport()
        report.record(path="a.jpg", outcome=FileOutcome.ADDED)
        report.record(path="b.jpg", outcome=FileOutcome.MISSING)

        report.raise_if_all_failed()

    def test_raise_if_all_failed__no_raise_when_nothing_attempted(self) -> None:
        report = FileOutcomeReport()

        report.raise_if_all_failed()

    def test_raise_if_all_failed__no_raise_when_all_already_present(self) -> None:
        report = FileOutcomeReport()
        report.record(path="a.jpg", outcome=FileOutcome.ALREADY_PRESENT)
        report.record(path="b.jpg", outcome=FileOutcome.ALREADY_PRESENT)

        report.raise_if_all_failed()

    def test_raise_if_all_failed__no_raise_when_already_present_and_failed(
        self,
    ) -> None:
        report = FileOutcomeReport()
        report.record(path="a.jpg", outcome=FileOutcome.ALREADY_PRESENT)
        report.record(path="b.jpg", outcome=FileOutcome.MISSING)
        report.record(path="c.jpg", outcome=FileOutcome.BROKEN)

        report.raise_if_all_failed()

    def test_log_summary(self, caplog: pytest.LogCaptureFixture) -> None:
        report = FileOutcomeReport()
        report.record(path="a.jpg", outcome=FileOutcome.ADDED)
        report.record(path="b.jpg", outcome=FileOutcome.MISSING)

        with caplog.at_level(logging.INFO):
            report.log_summary()

        text = caplog.text
        assert "added=1" in text
        assert "missing=1" in text
        assert "a.jpg" in text
        assert "b.jpg" in text
