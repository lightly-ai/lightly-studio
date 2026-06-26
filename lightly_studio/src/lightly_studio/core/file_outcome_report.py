"""Central, I/O-agnostic per-run report of file outcomes.

Pipeline steps route each per-item file operation through
`FileOutcomeReport.track`. The report does pure bookkeeping and decides the
raise policy; it has no knowledge of I/O. Classifying *why* a file failed lives
at the I/O boundary, which raises the typed input errors from
`lightly_studio.errors`.

Usage::

    report = FileOutcomeReport()
    for path in paths:
        with report.track(path):
            operation(path)  # raises MissingInputFileError / BrokenInputFileError
    report.raise_if_all_failed()
    report.log_summary()
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from os import PathLike

from lightly_studio.errors import (
    AllInputFilesFailedError,
    BrokenInputFileError,
    MissingInputFileError,
)

logger = logging.getLogger(__name__)

# Maximum number of example paths kept per outcome for the summary.
DEFAULT_MAX_EXAMPLES_PER_OUTCOME = 5


class FileOutcome(Enum):
    """The outcome of attempting to process a single input file."""

    ADDED = "added"
    ALREADY_PRESENT = "already_present"
    MISSING = "missing"
    BROKEN = "broken"


@dataclass
class TrackedFile:
    """Mutable handle yielded by `FileOutcomeReport.track`.

    Attributes:
        outcome: The success outcome to record on clean exit. Defaults to
            `FileOutcome.ADDED`; set it to `FileOutcome.ALREADY_PRESENT` from
            the tracked body when the file was already present.
    """

    outcome: FileOutcome = FileOutcome.ADDED


@dataclass
class FileOutcomeReport:
    """Per-run bookkeeping of file outcomes plus the all-failed raise policy.

    The report counts how many files ended in each `FileOutcome` and keeps a
    capped list of example paths per outcome for the end-of-run summary. It has
    no I/O dependency and never catches a catch-all `Exception`: only the typed
    input errors are tolerated, everything else propagates.

    Attributes:
        max_examples_per_outcome: Maximum number of example paths kept per
            outcome.
    """

    max_examples_per_outcome: int = DEFAULT_MAX_EXAMPLES_PER_OUTCOME
    _counts: dict[FileOutcome, int] = field(
        default_factory=lambda: dict.fromkeys(FileOutcome, 0)
    )
    _example_paths: dict[FileOutcome, list[str]] = field(
        default_factory=lambda: {outcome: [] for outcome in FileOutcome}
    )

    def record(self, path: str | PathLike[str], outcome: FileOutcome) -> None:
        """Record a single file outcome.

        Increments the per-outcome count and keeps up to
        `max_examples_per_outcome` example paths for that outcome.

        Args:
            path: The path of the file the outcome refers to.
            outcome: The outcome to record.
        """
        self._counts[outcome] += 1
        examples = self._example_paths[outcome]
        if len(examples) < self.max_examples_per_outcome:
            examples.append(str(path))

    @contextmanager
    def track(self, path: str | PathLike[str]) -> Iterator[TrackedFile]:
        """Track a single per-item file operation.

        On a clean exit, records the success outcome carried by the yielded
        `TrackedFile` (default `FileOutcome.ADDED`; the body may set it to
        `FileOutcome.ALREADY_PRESENT`). A `MissingInputFileError` is recorded as
        `FileOutcome.MISSING` and a `BrokenInputFileError` as
        `FileOutcome.BROKEN`, then suppressed so the loop continues. Any other
        exception propagates: a bug or infra failure is not a broken file.

        Args:
            path: The path of the file being processed.

        Yields:
            A `TrackedFile` handle whose `outcome` selects the success outcome.
        """
        tracked = TrackedFile()
        try:
            yield tracked
        except MissingInputFileError:
            self.record(path=path, outcome=FileOutcome.MISSING)
        except BrokenInputFileError:
            self.record(path=path, outcome=FileOutcome.BROKEN)
        else:
            self.record(path=path, outcome=tracked.outcome)

    def raise_if_all_failed(self) -> None:
        """Raise if at least one file was attempted and none succeeded.

        A file is "attempted" if it was added, missing, or broken;
        already-present files are excluded. So a run that only skips
        already-present files (0 attempted) does not raise.

        Raises:
            AllInputFilesFailedError: If at least one file was attempted and
                zero of them succeeded.
        """
        n_added = self._counts[FileOutcome.ADDED]
        n_missing = self._counts[FileOutcome.MISSING]
        n_broken = self._counts[FileOutcome.BROKEN]
        n_attempted = n_added + n_missing + n_broken
        if n_attempted >= 1 and n_added == 0:
            raise AllInputFilesFailedError(
                f"All {n_attempted} attempted input files failed "
                f"({n_missing} missing, {n_broken} broken)."
            )

    def log_summary(self) -> None:
        """Log a single end-of-run summary of counts and example paths."""
        counts = ", ".join(f"{outcome.value}={self._counts[outcome]}" for outcome in FileOutcome)
        logger.info(f"File outcomes: {counts}.")
        for outcome in FileOutcome:
            examples = self._example_paths[outcome]
            if examples:
                logger.info(f"Example {outcome.value} paths: {', '.join(examples)}.")
