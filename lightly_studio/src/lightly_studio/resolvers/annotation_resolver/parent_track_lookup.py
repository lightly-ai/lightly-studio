"""Batch-fetch one class name per parent object track."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session, col, func, select

from lightly_studio.database import db_array
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation_label import AnnotationLabelTable


def fetch_parent_track_class_names(
    session: Session,
    annotations: Sequence[AnnotationBaseTable],
) -> dict[UUID, str]:
    """Return one class name per parent object track, looked up in a single query.

    Collects distinct ``parent_object_track_id`` values from the given annotations,
    runs a ``GROUP BY`` query with ``MIN(annotation_label_name)``, and returns the
    mapping. Portable across PostgreSQL and DuckDB.

    Args:
        session: Database session.
        annotations: Annotations whose parent tracks to look up.

    Returns:
        Mapping from parent object track ID to its class name.
    """
    parent_track_ids = {
        annotation.object_track.parent_object_track_id
        for annotation in annotations
        if annotation.object_track and annotation.object_track.parent_object_track_id
    }
    if not parent_track_ids:
        return {}

    rows = session.exec(
        select(
            col(AnnotationBaseTable.object_track_id),
            func.min(col(AnnotationLabelTable.annotation_label_name)),
        )
        .join(
            AnnotationLabelTable,
            col(AnnotationLabelTable.annotation_label_id)
            == col(AnnotationBaseTable.annotation_label_id),
        )
        .where(
            db_array.in_array(
                column=col(AnnotationBaseTable.object_track_id),
                values=list(parent_track_ids),
            )
        )
        .group_by(col(AnnotationBaseTable.object_track_id))
    ).all()

    return {track_id: class_name for track_id, class_name in rows if track_id is not None}
