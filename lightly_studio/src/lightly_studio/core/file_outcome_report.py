"""Central, I/O-agnostic per-run report of file outcomes.

Pipeline steps route each per-item file operation through
`FileOutcomeReport.track`. The body classifies *why* a file ended where it did
by raising one of the typed signals defined here; the report does pure
bookkeeping. It has no knowledge of I/O.

Each tracked file ends in exactly one `FileOutcome`:

- clean exit (no exception)        -> `ADDED`
- `AlreadyPresentInputFileError`   -> `ALREADY_PRESENT` (success, skipped work)
- `MissingInputFileError`          -> `MISSING` (tolerated failure)
- `BrokenInputFileError`           -> `BROKEN` (tolerated failure)

The four signals are caught inside `track` so the loop continues; any other
exception propagates, because a bug or infra failure is not a file outcome.

Usage::

    report = FileOutcomeReport()
    for path in paths:
        with report.track(path):
            if not fs.exists(path):
                raise MissingInputFileError("File does not exist.")
            if dataset.contains(path):
                raise AlreadyPresentInputFileError("Already added.")
            try:
                with PILImage.open(path) as image:
                    dataset.add(path, image)
            except (OSError, PILImage.UnidentifiedImageError) as exc:
                raise BrokenInputFileError("Could not decode image.") from exc
    report.log_summary()
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import Enum
from os import PathLike

logger = logging.getLogger(__name__)

# Maximum number of example paths kept per outcome for the summary.
DEFAULT_MAX_EXAMPLES_PER_OUTCOME = 5


class InputFileError(Exception):
    """Base for the per-item signals raised inside `FileOutcomeReport.track`."""


class AlreadyPresentInputFileError(InputFileError):
    """Signal that the input file was already present, so no work was done."""


class MissingInputFileError(InputFileError):
    """Signal that an input file path does not resolve.

    Detect this proactively with `fs.exists()` rather than relying on
    `FileNotFoundError`, which is unreliable across fsspec backends and is a
    subclass of `OSError`.
    """


class BrokenInputFileError(InputFileError):
    """Signal that an input file is present but unreadable/undecodable."""


class FileOutcome(Enum):
    """The outcome of attempting to process a single input file."""

    ADDED = "added"
    ALREADY_PRESENT = "already_present"
    MISSING = "missing"
    BROKEN = "broken"


@dataclass
class FileOutcomeReport:
    """Per-run bookkeeping of file outcomes.

    The report counts how many files ended in each `FileOutcome` and keeps a
    capped list of example paths per outcome for the end-of-run summary. It has
    no I/O dependency and never catches a catch-all `Exception`: only the typed
    input signals are tolerated, everything else propagates.

    Attributes:
        max_examples_per_outcome: Maximum number of example paths kept per
            outcome.
    """

    max_examples_per_outcome: int = DEFAULT_MAX_EXAMPLES_PER_OUTCOME
    _counts: dict[FileOutcome, int] = field(
        default_factory=lambda: dict.fromkeys(FileOutcome, 0),
        init=False,
        repr=False,
        compare=False,
    )
    _example_paths: dict[FileOutcome, list[str]] = field(
        default_factory=lambda: {outcome: [] for outcome in FileOutcome},
        init=False,
        repr=False,
        compare=False,
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

    @contextlib.contextmanager
    def track(self, path: str | PathLike[str]) -> Iterator[None]:
        """Track a single per-item file operation.

        Records the outcome from how the tracked body exits: a clean exit is
        `FileOutcome.ADDED`, and each input signal maps to its matching outcome
        and is suppressed so the loop continues. Any other exception propagates:
        a bug or infra failure is not a file outcome.

        Args:
            path: The path of the file being processed.
        """
        try:
            yield
        except AlreadyPresentInputFileError:
            self.record(path=path, outcome=FileOutcome.ALREADY_PRESENT)
        except MissingInputFileError:
            self.record(path=path, outcome=FileOutcome.MISSING)
        except BrokenInputFileError:
            self.record(path=path, outcome=FileOutcome.BROKEN)
        else:
            self.record(path=path, outcome=FileOutcome.ADDED)

    def log_summary(self) -> None:
        """Log a single end-of-run summary of counts and example paths."""
        counts = ", ".join(f"{outcome.value}={self._counts[outcome]}" for outcome in FileOutcome)
        logger.info(f"File outcomes: {counts}.")
        for outcome in FileOutcome:
            examples = self._example_paths[outcome]
            if examples:
                logger.info(f"Example {outcome.value} paths: {', '.join(examples)}.")
