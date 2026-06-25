"""Central per-run file-outcome report and error-handling wrapper for pipeline steps.

This is the single place where every pipeline step routes its per-item file operations,
so the error-handling decision ("on what to error, and how to handle it") lives in one
place instead of in N scattered try/except blocks.
"""

from __future__ import annotations

import dataclasses
import logging
from collections.abc import Callable
from enum import Enum

from lightly_studio.errors import AllInputFilesFailedError

logger = logging.getLogger(__name__)

# Number of example paths kept and shown per outcome in the end-of-run summary.
MAX_EXAMPLE_PATHS_PER_OUTCOME = 5


class FileOutcome(Enum):
    """The outcome of attempting to add a single input file to a dataset."""

    ADDED = "added"
    """The file was newly added."""

    ALREADY_PRESENT = "already_present"
    """The file was already present and therefore not added again."""

    MISSING = "missing"
    """The path does not resolve to an existing file."""

    BROKEN = "broken"
    """The file is present but unreadable or undecodable."""


# Outcomes that represent an attempt to process the file (as opposed to a skip because the
# file was already present). The all-failed raise rule is computed over these.
_ATTEMPTED_OUTCOMES = (FileOutcome.ADDED, FileOutcome.MISSING, FileOutcome.BROKEN)


@dataclasses.dataclass
class FileOutcomeReport:
    """Per-run report recording one outcome per file and owning error-handling policy.

    Pipeline steps route each per-item file operation through `process_file`, which catches
    the failure, classifies it into an outcome, applies the skip policy, and records it. At
    the end of the run, `raise_if_all_failed` enforces the all-failed rule and `log_summary`
    logs counts and example paths per outcome.

    Attributes:
        counts: Number of files recorded per outcome.
        example_paths: Up to `MAX_EXAMPLE_PATHS_PER_OUTCOME` example paths per outcome.
    """

    counts: dict[FileOutcome, int] = dataclasses.field(
        default_factory=lambda: dict.fromkeys(FileOutcome, 0)
    )
    example_paths: dict[FileOutcome, list[str]] = dataclasses.field(
        default_factory=lambda: {outcome: [] for outcome in FileOutcome}
    )

    def process_file(self, path: str, operation: Callable[[], FileOutcome]) -> FileOutcome | None:
        """Run a per-item file operation, classify any failure, and record the outcome.

        The operation performs the actual work for a single file and returns the success
        outcome (`ADDED` or `ALREADY_PRESENT`). A `FileNotFoundError` is classified as
        `MISSING`; any other exception is classified as `BROKEN`. Failures are tolerated:
        the bad item is recorded and skipped, no exception propagates and no placeholder
        is created.

        Args:
            path: The path of the file being processed, used for the recorded examples.
            operation: A callable performing the work for a single file. Returns the
                success outcome of the file.

        Returns:
            The recorded outcome, or `None` if the operation failed and was skipped.
        """
        try:
            outcome = operation()
        except FileNotFoundError:
            self.record(path=path, outcome=FileOutcome.MISSING)
            return None
        except Exception:
            # Any non-missing failure means the file is present but could not be read or
            # decoded. We tolerate it instead of crashing the whole run.
            logger.debug(f"Failed to process file: {path}", exc_info=True)
            self.record(path=path, outcome=FileOutcome.BROKEN)
            return None
        self.record(path=path, outcome=outcome)
        return outcome

    def record(self, path: str, outcome: FileOutcome) -> None:
        """Record a single file's outcome.

        Args:
            path: The path of the file.
            outcome: The outcome to record for the file.
        """
        self.counts[outcome] += 1
        examples = self.example_paths[outcome]
        if len(examples) < MAX_EXAMPLE_PATHS_PER_OUTCOME:
            examples.append(path)

    @property
    def n_attempted(self) -> int:
        """Number of files that were actually attempted (added, missing, or broken)."""
        return sum(self.counts[outcome] for outcome in _ATTEMPTED_OUTCOMES)

    @property
    def n_succeeded(self) -> int:
        """Number of files that were successfully added."""
        return self.counts[FileOutcome.ADDED]

    def raise_if_all_failed(self) -> None:
        """Raise if every attempted file failed, signalling a wrong path or real bug.

        This is distinct from "nothing was attempted because all files were already
        present", which does not raise.

        Raises:
            AllInputFilesFailedError: If at least one file was attempted and none
                succeeded.
        """
        if self.n_attempted > 0 and self.n_succeeded == 0:
            raise AllInputFilesFailedError(
                f"All {self.n_attempted} attempted input files failed to be added "
                f"({self.counts[FileOutcome.MISSING]} missing, "
                f"{self.counts[FileOutcome.BROKEN]} broken)."
            )

    def log_summary(self) -> None:
        """Log a single end-of-run summary with counts and example paths per outcome."""
        counts_summary = ", ".join(
            f"{outcome.value}: {self.counts[outcome]}" for outcome in FileOutcome
        )
        logger.info(f"File outcome summary - {counts_summary}.")
        for outcome in FileOutcome:
            examples = self.example_paths[outcome]
            if examples:
                logger.info(f"Example {outcome.value} paths: {', '.join(examples)}")
