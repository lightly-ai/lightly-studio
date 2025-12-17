"""Update status for one or many images."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal
from uuid import UUID

from sqlmodel import Session, col, update

from lightly_studio.models.image import ImageTable

StatusField = Literal["status_metadata", "status_embeddings"]


def update_status(
    session: Session,
    sample_ids: Iterable[UUID],
    status: str,
    status_field: StatusField = "status_embeddings",
) -> int:
    """Update the status for the given samples.

    Args:
        session: Active database session.
        sample_ids: Iterable of sample_ids whose status should be updated.
        status: New status value.
        status_field: Which status column to update (`status_metadata` or `status_embeddings`).

    Returns:
        Number of rows updated.
    """
    if status_field not in {"status_metadata", "status_embeddings"}:
        raise ValueError(f"Unknown status field: {status_field}")

    stmt = (
        update(ImageTable)
        .where(col(ImageTable.sample_id).in_(list(sample_ids)))
        .values({status_field: status})
    )
    result = session.exec(stmt)  # type: ignore
    session.commit()
    return result.rowcount or 0
