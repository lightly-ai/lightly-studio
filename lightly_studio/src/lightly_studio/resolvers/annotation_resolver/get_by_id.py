"""Handler for database operations related to annotations."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
)


def get_by_id(session: Session, annotation_id: UUID) -> AnnotationBaseTable | None:
    """Retrieve a single annotation by ID."""
    return session.exec(
        select(AnnotationBaseTable).where(AnnotationBaseTable.sample_id == annotation_id)
    ).one_or_none()


def get_by_ids(session: Session, annotation_ids: Sequence[UUID]) -> Sequence[AnnotationBaseTable]:
    """Retrieve multiple annotations by their IDs.

    Args:
        session: The database session to use for the query.
        annotation_ids: A list of annotation IDs to retrieve.

    Returns:
        A list of annotations matching the provided IDs.
    """
    return session.exec(
        select(AnnotationBaseTable).where(col(AnnotationBaseTable.sample_id).in_(annotation_ids))
    ).all()
