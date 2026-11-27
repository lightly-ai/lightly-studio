"""Handler for database operations related to annotations."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.database import db_array
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.resolvers import annotation_resolver


def delete_annotations(
    session: Session,
    annotation_label_ids: Sequence[UUID],
) -> None:
    """Delete the annotations with the given labels, their samples and dependent rows.

    Args:
        session: Database session.
        annotation_label_ids: IDs of the annotation labels to delete the annotations of.
            If empty, no annotations are deleted.
    """
    if not annotation_label_ids:
        return
    query = select(AnnotationBaseTable.sample_id).where(
        db_array.in_array(
            column=col(AnnotationBaseTable.annotation_label_id), values=annotation_label_ids
        )
    )
    annotation_resolver.delete_annotations_by_ids(
        session=session, annotation_ids=session.exec(query).all()
    )
