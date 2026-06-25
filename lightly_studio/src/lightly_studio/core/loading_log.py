"""Per-run report recording the outcome of every input file during loading."""

from __future__ import annotations

import enum
import logging
from collections.abc import Iterable
from dataclasses import dataclass, field

from lightly_studio.type_definitions import PathLike

logger = logging.getLogger(__name__)

# Constants
MAX_EXAMPLE_PATHS_TO_SHOW = 5


class FileOutcome(enum.Enum):
    """The single outcome recorded for each input file of a loading run."""

    ADDED = "added"
    ALREADY_PRESENT = "already-present"
    MISSING = "missing"
    BROKEN = "broken"


class AllInputFilesFailedError(RuntimeError):
    """Raised when every attempted input file failed and none were added.

    This is the wrong-path / real-bug case. It is distinct from a run where no file
    was attempted because everything was already present, which is not an error.
    """


@dataclass
class FileOutcomeReport:
    """Per-run report recording exactly one outcome per input file.

    Every loading pipeline writes to one report instead of returning per-file values.
    The report is the single place outcomes are recorded, the all-failed error is
    decided, and the end-of-run summary is logged.
    """

    counts: dict[FileOutcome, int] = field(default_factory=lambda: dict.fromkeys(FileOutcome, 0))
    example_paths: dict[FileOutcome, list[str]] = field(
        default_factory=lambda: {outcome: [] for outcome in FileOutcome}
    )

    def record(self, path: PathLike, outcome: FileOutcome) -> None:
        """Record a single file with one of the four outcomes."""
        self.counts[outcome] += 1
        examples = self.example_paths[outcome]
        if len(examples) < MAX_EXAMPLE_PATHS_TO_SHOW:
            examples.append(str(path))

    def record_many(self, paths: Iterable[PathLike], outcome: FileOutcome) -> None:
        """Record multiple files that share the same outcome."""
        for path in paths:
            self.record(path, outcome)

    @property
    def n_attempted(self) -> int:
        """Number of files that were attempted (added + missing + broken).

        Already-present files are skipped before being attempted, so they do not count.
        """
        return sum(self.counts.values()) - self.counts[FileOutcome.ALREADY_PRESENT]

    @property
    def n_added(self) -> int:
        """Number of files that were successfully added."""
        return self.counts[FileOutcome.ADDED]

    def raise_if_all_failed(self) -> None:
        """Raise if every attempted file failed (0 succeeded of N attempted).

        Does not raise when nothing was attempted (e.g. everything was already present).
        """
        if self.n_attempted > 0 and self.n_added == 0:
            raise AllInputFilesFailedError(
                f"None of the {self.n_attempted} attempted files could be added to the dataset. "
                "Check that the input paths are correct and the files are readable."
            )

    def log_summary(self) -> None:
        """Log a single end-of-run summary: counts per outcome plus example paths."""
        summary = ", ".join(f"{self.counts[outcome]} {outcome.value}" for outcome in FileOutcome)
        logger.info(f"File loading summary: {summary}.")

        for outcome in (FileOutcome.MISSING, FileOutcome.BROKEN, FileOutcome.ALREADY_PRESENT):
            examples = self.example_paths[outcome]
            if examples:
                logger.warning(f"Example {outcome.value} paths: {', '.join(examples)}")
