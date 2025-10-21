"""Handler for database operations related to annotations."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationCreate,
)
from lightly_studio.models.annotation.instance_segmentation import (
    InstanceSegmentationAnnotationTable,
)
from lightly_studio.models.annotation.object_detection import (
    ObjectDetectionAnnotationTable,
)
from lightly_studio.models.annotation.semantic_segmentation import (
    SemanticSegmentationAnnotationTable,
)


def create_many(
    session: Session,
    annotations: list[AnnotationCreate],
) -> Sequence[UUID]:
    """Create many annotations with object detection details in bulk."""
    # Step 1: Create all base annotations
    base_annotations = []
    object_detection_annotations = []
    instance_segmentation_annotations = []
    semantic_segmentation_annotations = []

    for annotation_create in annotations:
        # Create base annotation
        db_base_annotation = AnnotationBaseTable(
            annotation_label_id=annotation_create.annotation_label_id,
            annotation_type=annotation_create.annotation_type,
            confidence=annotation_create.confidence,
            dataset_id=annotation_create.dataset_id,
            sample_id=annotation_create.sample_id,
        )

        # Set other relationship details to None
        db_base_annotation.instance_segmentation_details = None
        db_base_annotation.semantic_segmentation_details = None
        db_base_annotation.object_detection_details = None

        base_annotations.append(db_base_annotation)

    # Bulk save base annotations and flush to get IDs
    session.bulk_save_objects(base_annotations)
    session.flush()

    # Step 2: Create specific annotation details
    for i, annotation_create in enumerate(annotations):
        # Create object detection details
        if base_annotations[i].annotation_type == "object_detection":
            db_object_detection = ObjectDetectionAnnotationTable(
                annotation_id=base_annotations[i].annotation_id,
                x=annotation_create.x,
                y=annotation_create.y,
                width=annotation_create.width,
                height=annotation_create.height,
            )
            object_detection_annotations.append(db_object_detection)

        # Create instance segmentation details
        elif base_annotations[i].annotation_type == "instance_segmentation":
            db_instance_segmentation = InstanceSegmentationAnnotationTable(
                annotation_id=base_annotations[i].annotation_id,
                segmentation_mask=annotation_create.segmentation_mask,
                x=annotation_create.x,
                y=annotation_create.y,
                width=annotation_create.width,
                height=annotation_create.height,
            )
            instance_segmentation_annotations.append(db_instance_segmentation)
        elif base_annotations[i].annotation_type == "semantic_segmentation":
            db_semantic_segmentation = SemanticSegmentationAnnotationTable(
                annotation_id=base_annotations[i].annotation_id,
                segmentation_mask=annotation_create.segmentation_mask,
            )
            semantic_segmentation_annotations.append(db_semantic_segmentation)

    # Bulk save object detection annotations
    session.bulk_save_objects(object_detection_annotations)
    session.bulk_save_objects(instance_segmentation_annotations)
    session.bulk_save_objects(semantic_segmentation_annotations)

    # Commit everything
    session.commit()

    return [annotation.annotation_id for annotation in base_annotations]
