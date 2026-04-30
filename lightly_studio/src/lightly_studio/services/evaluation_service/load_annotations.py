"""Annotation loaders for evaluation tasks."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
from lightly_studio.models.annotation.object_detection import ObjectDetectionAnnotationTable
from lightly_studio.models.annotation.segmentation import SegmentationAnnotationTable
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.services.evaluation_service import (
    compute_classification_metrics,
    compute_instance_segmentation_metrics,
    compute_od_metrics,
)


def load_object_detection_annotations(
    session: Session,
    collection_id: UUID,
    sample_ids: set[UUID] | None = None,
) -> list[compute_od_metrics.ODAnnotation]:
    """Load all object-detection annotations for one collection."""
    stmt = (
        select(AnnotationBaseTable)
        .join(SampleTable, col(SampleTable.sample_id) == col(AnnotationBaseTable.sample_id))
        .where(col(SampleTable.collection_id) == collection_id)
        .where(col(AnnotationBaseTable.annotation_type) == AnnotationType.OBJECT_DETECTION)
    )
    if sample_ids is not None:
        stmt = stmt.where(col(AnnotationBaseTable.parent_sample_id).in_(sample_ids))
    ann_rows = list(session.exec(stmt).all())
    if not ann_rows:
        return []

    sample_ids = {annotation.sample_id for annotation in ann_rows}
    bbox_rows = session.exec(
        select(ObjectDetectionAnnotationTable).where(
            col(ObjectDetectionAnnotationTable.sample_id).in_(sample_ids)
        )
    ).all()
    bbox_map = {row.sample_id: (row.x, row.y, row.width, row.height) for row in bbox_rows}

    result: list[compute_od_metrics.ODAnnotation] = []
    for annotation in ann_rows:
        bbox = bbox_map.get(annotation.sample_id)
        if bbox is None:
            continue
        result.append(
            compute_od_metrics.ODAnnotation(
                annotation_id=annotation.sample_id,
                sample_id=annotation.parent_sample_id,
                label_id=annotation.annotation_label_id,
                confidence=annotation.confidence or 0.0,
                x=bbox[0],
                y=bbox[1],
                w=bbox[2],
                h=bbox[3],
            )
        )
    return result


def load_classification_annotations(
    session: Session,
    collection_id: UUID,
    sample_ids: set[UUID] | None = None,
) -> list[compute_classification_metrics.ClassificationAnnotation]:
    """Load all classification annotations for one collection."""
    stmt = (
        select(AnnotationBaseTable)
        .join(SampleTable, col(SampleTable.sample_id) == col(AnnotationBaseTable.sample_id))
        .where(col(SampleTable.collection_id) == collection_id)
        .where(col(AnnotationBaseTable.annotation_type) == AnnotationType.CLASSIFICATION)
    )
    if sample_ids is not None:
        stmt = stmt.where(col(AnnotationBaseTable.parent_sample_id).in_(sample_ids))
    ann_rows = list(session.exec(stmt).all())
    return [
        compute_classification_metrics.ClassificationAnnotation(
            annotation_id=annotation.sample_id,
            sample_id=annotation.parent_sample_id,
            label_id=annotation.annotation_label_id,
            confidence=annotation.confidence or 0.0,
        )
        for annotation in ann_rows
    ]


def load_instance_segmentation_annotations(
    session: Session,
    collection_id: UUID,
    sample_ids: set[UUID] | None = None,
) -> list[compute_instance_segmentation_metrics.InstanceSegmentationAnnotation]:
    """Load all instance-segmentation annotations for one collection."""
    stmt = (
        select(AnnotationBaseTable)
        .join(SampleTable, col(SampleTable.sample_id) == col(AnnotationBaseTable.sample_id))
        .where(col(SampleTable.collection_id) == collection_id)
        .where(col(AnnotationBaseTable.annotation_type) == AnnotationType.SEGMENTATION_MASK)
    )
    if sample_ids is not None:
        stmt = stmt.where(col(AnnotationBaseTable.parent_sample_id).in_(sample_ids))
    ann_rows = list(session.exec(stmt).all())
    if not ann_rows:
        return []

    annotation_ids = {annotation.sample_id for annotation in ann_rows}
    segmentation_rows = session.exec(
        select(SegmentationAnnotationTable).where(
            col(SegmentationAnnotationTable.sample_id).in_(annotation_ids)
        )
    ).all()
    segmentation_map = {
        row.sample_id: (row.x, row.y, row.width, row.height, row.segmentation_mask)
        for row in segmentation_rows
    }

    parent_sample_ids = {annotation.parent_sample_id for annotation in ann_rows}
    image_rows = session.exec(
        select(ImageTable).where(col(ImageTable.sample_id).in_(parent_sample_ids))
    ).all()
    image_map = {row.sample_id: (row.width, row.height) for row in image_rows}

    result: list[compute_instance_segmentation_metrics.InstanceSegmentationAnnotation] = []
    for annotation in ann_rows:
        segmentation = segmentation_map.get(annotation.sample_id)
        image_size = image_map.get(annotation.parent_sample_id)
        if segmentation is None or image_size is None or segmentation[4] is None:
            continue
        result.append(
            compute_instance_segmentation_metrics.InstanceSegmentationAnnotation(
                annotation_id=annotation.sample_id,
                sample_id=annotation.parent_sample_id,
                label_id=annotation.annotation_label_id,
                confidence=annotation.confidence or 0.0,
                image_width=image_size[0],
                image_height=image_size[1],
                x=segmentation[0],
                y=segmentation[1],
                width=segmentation[2],
                height=segmentation[3],
                segmentation_mask=list(segmentation[4]),
            )
        )
    return result


def load_label_names(session: Session, label_ids: set[UUID]) -> dict[UUID, str]:
    """Load human-readable label names for the given label IDs."""
    if not label_ids:
        return {}
    rows = session.exec(
        select(AnnotationLabelTable).where(
            col(AnnotationLabelTable.annotation_label_id).in_(label_ids)
        )
    ).all()
    return {row.annotation_label_id: row.annotation_label_name for row in rows}
