"""Implementation of get_sample_ids_by_paths function for images."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.utils import batching


def get_sample_ids_by_paths(
    session: Session,
    collection_id: UUID,
    file_paths_abs: Sequence[str],
) -> dict[str, UUID]:
    """Get sample IDs for images with given absolute file paths in a collection.

    Args:
        session: The database session.
        collection_id: The ID of the collection to scope results to.
        file_paths_abs: The absolute file paths to look up.

    Returns:
        A mapping from file_path_abs to sample_id for paths that exist in the collection.
        Paths not found in the collection are omitted from the result.
    """
    path_to_sample_id: dict[str, UUID] = {}
    for batch in batching.batched(items=file_paths_abs):
        query = (
            select(col(ImageTable.file_path_abs), col(ImageTable.sample_id))
            .join(SampleTable)
            .where(
                col(SampleTable.collection_id) == collection_id,
                col(ImageTable.file_path_abs).in_(batch),
            )
        )
        path_to_sample_id.update(session.exec(query).all())
    return path_to_sample_id
