"""Functions to add samples and their annotations to a dataset in the database."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from sqlmodel import Session

from lightly_studio.resolvers import (
    sample_resolver,
    image_resolver,
)

# Constants
ANNOTATION_BATCH_SIZE = 64  # Number of annotations to process in a single batch
SAMPLE_BATCH_SIZE = 32  # Number of samples to process in a single batch
MAX_EXAMPLE_PATHS_TO_SHOW = 5


@dataclass
class _LoadingLoggingContext:
    """Context for the logging while loading data."""

    n_samples_before_loading: int
    n_samples_to_be_inserted: int = 0
    example_paths_not_inserted: list[str] = field(default_factory=list)

    def update_example_paths(self, example_paths_not_inserted: list[str]) -> None:
        if len(self.example_paths_not_inserted) >= MAX_EXAMPLE_PATHS_TO_SHOW:
            return
        upper_limit = MAX_EXAMPLE_PATHS_TO_SHOW - len(self.example_paths_not_inserted)
        self.example_paths_not_inserted.extend(example_paths_not_inserted[:upper_limit])


def _log_loading_results(
    session: Session, dataset_id: UUID, logging_context: _LoadingLoggingContext
) -> None:
<<<<<<< HEAD
<<<<<<< HEAD
    n_samples_end = sample_resolver.count_by_dataset_id(session=session, dataset_id=dataset_id)
=======
    n_samples_end = image_resolver.count_by_dataset_id(session=session, dataset_id=dataset_id)
>>>>>>> ea65d70 (Add videos from path)
=======
    n_samples_end = sample_resolver.count_by_dataset_id(session=session, dataset_id=dataset_id)
>>>>>>> 3cc6de2 (fix)
    n_samples_inserted = n_samples_end - logging_context.n_samples_before_loading
    print(
        f"Added {n_samples_inserted} out of {logging_context.n_samples_to_be_inserted}"
        " new samples to the dataset."
    )
    if logging_context.example_paths_not_inserted:
        # TODO(Jonas, 09/2025): Use logging instead of print
        print(
            f"Examples of paths that were not added: "
            f" {', '.join(logging_context.example_paths_not_inserted)}"
        )
