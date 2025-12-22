"""Functions to add samples and their annotations to a dataset in the database."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from uuid import UUID

from sqlmodel import Session

from lightly_studio.resolvers import (
    sample_resolver,
)

logger = logging.getLogger(__name__)

# Constants
MAX_EXAMPLE_PATHS_TO_SHOW = 5


@dataclass
class LoadingLoggingContext:
    """Context for the logging while loading data."""

    n_samples_before_loading: int
    n_samples_to_be_inserted: int = 0
    example_paths_not_inserted: list[str] = field(default_factory=list)

    def update_example_paths(self, example_paths_not_inserted: list[str]) -> None:
        """Update the list of example paths that were not inserted."""
        if len(self.example_paths_not_inserted) >= MAX_EXAMPLE_PATHS_TO_SHOW:
            return
        upper_limit = MAX_EXAMPLE_PATHS_TO_SHOW - len(self.example_paths_not_inserted)
        self.example_paths_not_inserted.extend(example_paths_not_inserted[:upper_limit])


def log_loading_results(
    session: Session, dataset_id: UUID, logging_context: LoadingLoggingContext
) -> None:
    """Log the results of loading samples into a dataset.

    Calculates how many samples were successfully inserted by comparing the
    current sample count with the count before loading. Prints a summary message
    and, if any paths failed to be inserted, prints examples of those paths.
    """
    n_samples_end = sample_resolver.count_by_collection_id(
        session=session, collection_id=dataset_id
    )
    n_samples_inserted = n_samples_end - logging_context.n_samples_before_loading
    logger.info(
        f"Added {n_samples_inserted} out of {logging_context.n_samples_to_be_inserted} "
        "new samples to the dataset."
    )
    if logging_context.example_paths_not_inserted:
        logger.warning(
            "Examples of paths that were not added: "
            f"{', '.join(logging_context.example_paths_not_inserted)}"
        )
