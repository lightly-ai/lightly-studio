"""Get annotation label IDs associated with samples."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import or_
from sqlmodel import Session, col, select

from lightly_studio.database import db_array
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable


def get_label_ids_by_sample_ids(
    session: Session,
    sample_ids: Sequence[UUID],
    annotation_label_ids: Sequence[UUID],
) -> dict[UUID, set[UUID]]:
    """Return selected annotation labels associated with each requested sample.

    A plotted parent sample is associated with labels from its child annotations.
    A plotted annotation sample is associated with its own label.
    """
    if not sample_ids or not annotation_label_ids:
        return {}

    requested_sample_ids = set(sample_ids)
    rows = session.exec(
        select(
            AnnotationBaseTable.sample_id,
            AnnotationBaseTable.parent_sample_id,
            AnnotationBaseTable.annotation_label_id,
        )
        .where(
            db_array.in_array(
                column=col(AnnotationBaseTable.annotation_label_id),
                values=annotation_label_ids,
            )
        )
        .where(
            or_(
                db_array.in_array(
                    column=col(AnnotationBaseTable.parent_sample_id), values=sample_ids
                ),
                db_array.in_array(column=col(AnnotationBaseTable.sample_id), values=sample_ids),
            )
        )
    ).all()

    sample_to_labels: dict[UUID, set[UUID]] = defaultdict(set)
    for annotation_id, parent_sample_id, annotation_label_id in rows:
        if parent_sample_id in requested_sample_ids:
            sample_to_labels[parent_sample_id].add(annotation_label_id)
        if annotation_id in requested_sample_ids:
            sample_to_labels[annotation_id].add(annotation_label_id)
    return dict(sample_to_labels)
