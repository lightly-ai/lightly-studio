"""filter_new_paths: split file paths into new vs. already-present for a collection."""

from __future__ import annotations

from uuid import UUID

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
    collection = session.get(CollectionTable, collection_id)
    if collection is None:
        raise ValueError(f"Collection with id {collection_id} not found.")
    column = SAMPLE_TYPE_TO_COLUMN.get(collection.sample_type)
    if column is None:
        raise ValueError(
            f"filter_new_paths does not support sample type {collection.sample_type}; "
            f"supported types are {sorted(t for t in SAMPLE_TYPE_TO_COLUMN)}."
        )

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
