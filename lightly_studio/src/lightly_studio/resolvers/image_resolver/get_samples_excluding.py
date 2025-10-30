"""Implementation of get_samples_excluding function for images."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session, col, func, select

from lightly_studio.models.image import ImageTable


def get_samples_excluding(
    session: Session,
    dataset_id: UUID,
    excluded_sample_ids: list[UUID],
    limit: int | None = None,
) -> Sequence[ImageTable]:
    """Get random samples excluding specified sample IDs.

    Args:
        session: The database session.
        dataset_id: The dataset ID to filter by.
        excluded_sample_ids: List of sample IDs to exclude from the result.
        limit: Maximum number of samples to return.
                If None, returns all matches.

    Returns:
        List of samples not associated with the excluded IDs.
    """
    query = (
        select(ImageTable)
        .where(ImageTable.dataset_id == dataset_id)
        .where(col(ImageTable.sample_id).not_in(excluded_sample_ids))
        .order_by(func.random())
    )

    if limit is not None:
        query = query.limit(limit)

    return session.exec(query).all()
