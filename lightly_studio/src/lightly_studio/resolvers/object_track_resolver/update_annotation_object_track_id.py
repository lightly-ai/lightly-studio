"""Helper for updating an annotation's object_track_id in DuckDB.

DuckDB performs over-eager foreign key checks, which can reject direct UPDATEs on
`annotation_base` when other tables hold FK references to it. We therefore use a
delete-and-reinsert pattern when changing the track association.
See https://duckdb.org/docs/stable/sql/indexes.html#over-eager-constraint-checking-in-foreign-keys
"""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationType,
)
from lightly_studio.models.annotation.object_detection import ObjectDetectionAnnotationTable
from lightly_studio.models.annotation.segmentation import SegmentationAnnotationTable
from lightly_studio.resolvers import annotation_resolver


def update_annotation_object_track_id(
    session: Session,
    *,
    annotation: AnnotationBaseTable,
    object_track_id: UUID | None,
    flush: bool = False,
) -> AnnotationBaseTable:
    """Update an annotation's track association using delete-and-reinsert.

    Args:
        session: Database session for executing the operation.
        annotation: The annotation to update.
        object_track_id: Track ID to set, or None to unlink.
        flush: Whether to call session.flush() after commit (kept for backwards
            compatibility with the previous resolver implementations).

    Returns:
        A copy of the annotation with the updated object_track_id.
    """
    session.refresh(annotation)
    annotation_copy = annotation.model_copy(update={"object_track_id": object_track_id})

    annotation_type = annotation_copy.annotation_type

    seg_details = annotation_copy.segmentation_details
    segmentation = (
        SegmentationAnnotationTable(
            sample_id=annotation_copy.sample_id,
            segmentation_mask=seg_details.segmentation_mask,
            x=seg_details.x,
            y=seg_details.y,
            width=seg_details.width,
            height=seg_details.height,
        )
        if annotation_type
        in (AnnotationType.INSTANCE_SEGMENTATION, AnnotationType.SEMANTIC_SEGMENTATION)
        and seg_details
        else None
    )

    od_details = annotation_copy.object_detection_details
    object_detection = (
        ObjectDetectionAnnotationTable(
            sample_id=annotation_copy.sample_id,
            x=od_details.x,
            y=od_details.y,
            width=od_details.width,
            height=od_details.height,
        )
        if annotation_type == AnnotationType.OBJECT_DETECTION and od_details
        else None
    )

    annotation_resolver.delete_annotation(session, annotation.sample_id, delete_sample=False)

    new_annotation = AnnotationBaseTable(
        sample_id=annotation_copy.sample_id,
        annotation_label_id=annotation_copy.annotation_label_id,
        annotation_type=annotation_copy.annotation_type,
        confidence=annotation_copy.confidence,
        created_at=annotation_copy.created_at,
        parent_sample_id=annotation_copy.parent_sample_id,
        object_track_id=object_track_id,
    )
    session.add(new_annotation)

    if segmentation:
        session.add(segmentation)

    if object_detection:
        session.add(object_detection)

    session.commit()
    if flush:
        session.flush()

    return annotation_copy
