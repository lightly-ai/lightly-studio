"""filter_new_paths / get_existing_paths: which file paths a collection already has."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Mapped
from sqlmodel import Session, col, select

from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.video import VideoTable
from lightly_studio.utils import batching

# Sample sub-type table that stores ``file_path_abs`` for each collection type.
SAMPLE_TYPE_TO_COLUMN = {
    SampleType.IMAGE: col(ImageTable.file_path_abs),
    SampleType.VIDEO: col(VideoTable.file_path_abs),
}


def filter_new_paths(
    session: Session, collection_id: UUID, file_paths_abs: list[str]
) -> tuple[list[str], list[str]]:
    """Return file paths that do not already exist in the given collection and those that do.

    The sample sub-type table (image or video) is derived from the collection's
    ``sample_type``, so callers only pass the collection.

    Args:
        session: The database session.
        collection_id: The collection ID to check for existing paths.
        file_paths_abs: The absolute file paths to filter.

    Returns:
        A tuple of (new_paths, existing_paths) where new_paths are file paths
        not yet in the collection and existing_paths are already present.
    """
    column = _resolve_path_column(session=session, collection_id=collection_id)

    existing_file_paths_abs: set[str] = set()
    for batch in batching.batched(items=file_paths_abs):
        existing_file_paths_abs.update(
            session.exec(
                select(column)
                .join(SampleTable)
                .where(
                    col(SampleTable.collection_id) == collection_id,
                    column.in_(batch),
                )
            ).all()
        )
    file_paths_abs_set = set(file_paths_abs)
    return (
        list(file_paths_abs_set - existing_file_paths_abs),  # paths not in the collection
        list(file_paths_abs_set & existing_file_paths_abs),  # paths already in the collection
    )


def get_existing_paths(session: Session, collection_id: UUID) -> set[str]:
    """Return every file path already present in the given collection.

    Args:
        session: The database session.
        collection_id: The collection ID to look up.

    Returns:
        The set of absolute file paths already in the collection.
    """
    column = _resolve_path_column(session=session, collection_id=collection_id)
    return set(
        session.exec(
            select(column).join(SampleTable).where(col(SampleTable.collection_id) == collection_id)
        ).all()
    )


def _resolve_path_column(session: Session, collection_id: UUID) -> Mapped[str]:
    """Return the ``file_path_abs`` column for the sample sub-type backing a collection."""
    collection = session.get(CollectionTable, collection_id)
    if collection is None:
        raise ValueError(f"Collection with id {collection_id} not found.")
    column = SAMPLE_TYPE_TO_COLUMN.get(collection.sample_type)
    if column is None:
        raise ValueError(
            f"does not support sample type {collection.sample_type}; "
            f"supported types are {sorted(t.value for t in SAMPLE_TYPE_TO_COLUMN)}."
        )
    return column
