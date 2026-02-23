"""Link an existing annotation to a track."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationType,
)
from lightly_studio.models.annotation.object_detection import ObjectDetectionAnnotationTable
from lightly_studio.models.annotation.object_track import ObjectTrackTable
from lightly_studio.models.annotation.segmentation import SegmentationAnnotationTable
from lightly_studio.resolvers import annotation_resolver


def add_annotation_to_track(
    session: Session,
    annotation: AnnotationBaseTable,
    track: ObjectTrackTable,
) -> AnnotationBaseTable:
    """Link an existing annotation to a track by setting its tracking_id.

    Uses a delete-and-reinsert pattern to work around DuckDB's over-eager FK
    constraint checking, which rejects direct UPDATEs on annotation_base when
    other tables hold FK references to it.
    See https://duckdb.org/docs/stable/sql/indexes.html#over-eager-constraint-checking-in-foreign-keys

    Args:
        session: Database session for executing the operation.
        annotation: The annotation to link.
        track: The track to link the annotation to.

    Returns:
        The updated annotation with tracking_id set.
    """
    try:
        annotation_copy = annotation.model_copy(update={"object_track_id": track.object_track_id})
        annotation_type = annotation_copy.annotation_type

        segmentation = (
            SegmentationAnnotationTable(
                sample_id=annotation_copy.sample_id,
                segmentation_mask=annotation_copy.segmentation_details.segmentation_mask,
                x=annotation_copy.segmentation_details.x,
                y=annotation_copy.segmentation_details.y,
                width=annotation_copy.segmentation_details.width,
                height=annotation_copy.segmentation_details.height,
            )
            if annotation_type
            in (AnnotationType.INSTANCE_SEGMENTATION, AnnotationType.SEMANTIC_SEGMENTATION)
            and annotation_copy.segmentation_details
            else None
        )

        object_detection = (
            ObjectDetectionAnnotationTable(
                sample_id=annotation_copy.sample_id,
                x=annotation_copy.object_detection_details.x,
                y=annotation_copy.object_detection_details.y,
                width=annotation_copy.object_detection_details.width,
                height=annotation_copy.object_detection_details.height,
            )
            if annotation_type == AnnotationType.OBJECT_DETECTION
            and annotation_copy.object_detection_details
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
            object_track_id=track.object_track_id,
        )
        session.add(new_annotation)

        if segmentation:
            session.add(segmentation)

        if object_detection:
            session.add(object_detection)

        session.commit()
        session.flush()

        return annotation_copy
    except Exception:
        session.rollback()
        raise
