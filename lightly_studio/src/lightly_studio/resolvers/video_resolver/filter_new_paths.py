"""Implementation of filter_new_paths function for videos."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.sample import SampleTable
from lightly_studio.models.video import VideoTable


def filter_new_paths(
    session: Session, collection_id: UUID, file_paths_abs: list[str]
) -> tuple[list[str], list[str]]:
    """Return file paths that do not already exist in the given collection and those that do.

    Args:
        session: The database session.
        collection_id: The collection ID to check for existing paths.
        file_paths_abs: The absolute file paths to filter.

    Returns:
        A tuple of (new_paths, existing_paths) where new_paths are file paths
        not yet in the collection and existing_paths are already present.
    """
    existing_file_paths_abs = set(
        session.exec(
            select(col(VideoTable.file_path_abs))
            .join(SampleTable)
            .where(
                col(SampleTable.collection_id) == collection_id,
                col(VideoTable.file_path_abs).in_(file_paths_abs),
            )
        ).all()
    )
    file_paths_abs_set = set(file_paths_abs)
    return (
        list(file_paths_abs_set - existing_file_paths_abs),  # paths not in the collection
        list(file_paths_abs_set & existing_file_paths_abs),  # paths already in the collection
    )
