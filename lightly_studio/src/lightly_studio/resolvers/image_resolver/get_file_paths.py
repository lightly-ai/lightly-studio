"""Resolver for the file paths of the images an image filter matches."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers.image_filter import ImageFilter


def get_file_paths(
    session: Session, collection_id: UUID, image_filter: ImageFilter | None
) -> list[str]:
    """Return the file paths of the collection's images that the filter matches.

    Args:
        session: Database session.
        collection_id: ID of the image collection.
        image_filter: Filter to apply, or None for every image of the collection.

    Returns:
        The absolute file paths, ordered by path.
    """
    query = (
        select(ImageTable.file_path_abs)
        .join(SampleTable, col(SampleTable.sample_id) == col(ImageTable.sample_id))
        .where(col(SampleTable.collection_id) == collection_id)
    )
    if image_filter is not None:
        query = query.where(
            col(ImageTable.sample_id).in_(image_filter.build_sample_ids_query(collection_id))
        )
    return list(session.exec(query.order_by(col(ImageTable.file_path_abs))).all())
