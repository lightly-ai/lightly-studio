"""Get the IDs of all annotations that use an annotation label."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable


def get_ids_by_label_id(session: Session, label_id: UUID) -> list[UUID]:
    """Return the sample IDs of all annotations with the label, in any collection."""
    return list(
        session.exec(
            select(AnnotationBaseTable.sample_id).where(
                col(AnnotationBaseTable.annotation_label_id) == label_id
            )
        ).all()
    )
