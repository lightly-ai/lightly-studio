"""Bulk update annotation labels for all annotations in an object track."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import sqlalchemy
from sqlalchemy import update
from sqlmodel import Session, col, delete, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation.cuboid_3d import Cuboid3DAnnotationTable
from lightly_studio.models.annotation.object_detection import ObjectDetectionAnnotationTable
from lightly_studio.models.annotation.segmentation import SegmentationAnnotationTable
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.evaluation_annotation_metric import EvaluationAnnotationMetricTable
from lightly_studio.resolvers import annotation_resolver


def update_label_by_object_track_id(
    session: Session,
    object_track_id: UUID,
    annotation_label_id: UUID,
) -> None:
    """Set annotation_label_id for all track annotations that have a different label.

    Uses a bulk delete-and-reinsert strategy to work around DuckDB's over-eager FK
    constraint checking: DuckDB implements UPDATE as DELETE + INSERT internally, which
    fires FK violations when child tables still reference the rows being updated. The
    workaround is to delete all child FK references first, run the bulk UPDATE, then
    reinsert the child rows.

    DuckDB checks FK constraints against committed state, so the child-row deletes
    must be committed before the UPDATE. The UPDATE and child-row reinserts run in
    a single follow-up transaction; if that transaction fails, the child rows are
    restored from the captured data.


    Evaluation metrics that reference the updated annotations are not reinserted because
    a label change invalidates them.

    Args:
        session: Database session for executing the operation.
        object_track_id: UUID of the object track whose annotations to update.
        annotation_label_id: UUID of the label to assign to all track annotations.

    Raises:
        ValueError: If the annotation label does not exist.
    """
    if session.get(AnnotationLabelTable, annotation_label_id) is None:
        raise ValueError(f"Annotation label with ID {annotation_label_id} not found.")

    all_siblings = annotation_resolver.get_all_by_object_track_id(
        session=session, object_track_id=object_track_id
    )
    siblings = [s for s in all_siblings if s.annotation_label_id != annotation_label_id]
    if not siblings:
        return

    sibling_ids = [s.sample_id for s in siblings]

    # Capture child row data before deletion so it can be restored afterwards.
    od_data = _capture_object_detection(session=session, sample_ids=sibling_ids)
    seg_data = _capture_segmentation(session=session, sample_ids=sibling_ids)
    cuboid_data = _capture_cuboid_3d(session=session, sample_ids=sibling_ids)

    # Remove all rows that hold FK references to annotation_base.sample_id so the
    # UPDATE below does not trigger DuckDB's over-eager constraint check.
    # Evaluation metrics are not reinserted: a label change invalidates them.
    session.exec(
        delete(EvaluationAnnotationMetricTable).where(
            sqlalchemy.or_(
                col(EvaluationAnnotationMetricTable.pred_annotation_id).in_(sibling_ids),
                col(EvaluationAnnotationMetricTable.gt_annotation_id).in_(sibling_ids),
            )
        )
    )
    session.exec(
        delete(ObjectDetectionAnnotationTable).where(
            col(ObjectDetectionAnnotationTable.sample_id).in_(sibling_ids)
        )
    )
    session.exec(
        delete(SegmentationAnnotationTable).where(
            col(SegmentationAnnotationTable.sample_id).in_(sibling_ids)
        )
    )
    session.exec(
        delete(Cuboid3DAnnotationTable).where(
            col(Cuboid3DAnnotationTable.sample_id).in_(sibling_ids)
        )
    )
    # DuckDB checks FK constraints against committed state, so the deletes must be
    # committed before the UPDATE can run without FK violations.
    session.commit()

    try:
        session.execute(
            update(AnnotationBaseTable)
            .where(col(AnnotationBaseTable.sample_id).in_(sibling_ids))
            .values(annotation_label_id=annotation_label_id)
        )
        _reinsert_child_rows(
            session=session,
            od_data=od_data,
            seg_data=seg_data,
            cuboid_data=cuboid_data,
        )
        session.commit()
    except Exception:
        session.rollback()
        _reinsert_child_rows(
            session=session,
            od_data=od_data,
            seg_data=seg_data,
            cuboid_data=cuboid_data,
        )
        session.commit()
        raise


def _reinsert_child_rows(
    session: Session,
    od_data: list[dict[str, Any]],
    seg_data: list[dict[str, Any]],
    cuboid_data: list[dict[str, Any]],
) -> None:

    for d in od_data:
        session.add(ObjectDetectionAnnotationTable(**d))
    for d in seg_data:
        session.add(SegmentationAnnotationTable(**d))
    for d in cuboid_data:
        session.add(Cuboid3DAnnotationTable(**d))


def _capture_object_detection(session: Session, sample_ids: list[UUID]) -> list[dict[str, Any]]:
    rows = session.exec(
        select(ObjectDetectionAnnotationTable).where(
            col(ObjectDetectionAnnotationTable.sample_id).in_(sample_ids)
        )
    ).all()
    return [
        {"sample_id": r.sample_id, "x": r.x, "y": r.y, "width": r.width, "height": r.height}
        for r in rows
    ]


def _capture_segmentation(session: Session, sample_ids: list[UUID]) -> list[dict[str, Any]]:
    rows = session.exec(
        select(SegmentationAnnotationTable).where(
            col(SegmentationAnnotationTable.sample_id).in_(sample_ids)
        )
    ).all()
    return [
        {
            "sample_id": r.sample_id,
            "segmentation_mask": r.segmentation_mask,
            "x": r.x,
            "y": r.y,
            "width": r.width,
            "height": r.height,
        }
        for r in rows
    ]


def _capture_cuboid_3d(session: Session, sample_ids: list[UUID]) -> list[dict[str, Any]]:
    rows = session.exec(
        select(Cuboid3DAnnotationTable).where(
            col(Cuboid3DAnnotationTable.sample_id).in_(sample_ids)
        )
    ).all()
    return [
        {
            "sample_id": r.sample_id,
            "frame_id": r.frame_id,
            "px": r.px,
            "py": r.py,
            "pz": r.pz,
            "qx": r.qx,
            "qy": r.qy,
            "qz": r.qz,
            "qw": r.qw,
            "sx": r.sx,
            "sy": r.sy,
            "sz": r.sz,
            "interpolated": r.interpolated,
        }
        for r in rows
    ]
