"""Handler for database operations related to annotations."""

from __future__ import annotations

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
from lightly_studio.models.collection import SampleType
from lightly_studio.models.sample import SampleCreate
from lightly_studio.resolvers import collection_resolver, sample_resolver


def create_many(
    session: Session,
    parent_collection_id: UUID,
    annotations: list[AnnotationCreate],
) -> list[UUID]:
    """Create multiple annotations in bulk with their respective type-specific details.

    Creates base annotations and their associated type-specific details (object detection,
    instance segmentation, or semantic segmentation) in the annotation dataset child of
    the provided parent dataset.

    It is responsibility of the caller to ensure that all parent samples belong to the same
    dataset with ID `parent_collection_id`. This function does not perform this check for
    performance reasons.

    Args:
        session: SQLAlchemy session for database operations.
        parent_collection_id: UUID of the parent dataset.
        annotations: List of annotation objects to create.

    Returns:
        List of created annotation IDs.
    """
    # Step 1: Create all base annotations
    base_annotations = []
    object_detection_annotations = []
    instance_segmentation_annotations = []
    semantic_segmentation_annotations = []
    annotation_dataset_id = collection_resolver.get_or_create_child_dataset(
        session=session, dataset_id=parent_collection_id, sample_type=SampleType.ANNOTATION
    )

    sample_ids = sample_resolver.create_many(
        session=session,
        samples=[SampleCreate(dataset_id=annotation_dataset_id) for _ in annotations],
    )
    for annotation_create, sample_id in zip(annotations, sample_ids):
        # Create base annotation
        db_base_annotation = AnnotationBaseTable(
            sample_id=sample_id,
            annotation_label_id=annotation_create.annotation_label_id,
            annotation_type=annotation_create.annotation_type,
            confidence=annotation_create.confidence,
            dataset_id=annotation_dataset_id,
            parent_sample_id=annotation_create.parent_sample_id,
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
                sample_id=base_annotations[i].sample_id,
                x=annotation_create.x,
                y=annotation_create.y,
                width=annotation_create.width,
                height=annotation_create.height,
            )
            object_detection_annotations.append(db_object_detection)

        # Create instance segmentation details
        elif base_annotations[i].annotation_type == "instance_segmentation":
            db_instance_segmentation = InstanceSegmentationAnnotationTable(
                sample_id=base_annotations[i].sample_id,
                segmentation_mask=annotation_create.segmentation_mask,
                x=annotation_create.x,
                y=annotation_create.y,
                width=annotation_create.width,
                height=annotation_create.height,
            )
            instance_segmentation_annotations.append(db_instance_segmentation)
        elif base_annotations[i].annotation_type == "semantic_segmentation":
            db_semantic_segmentation = SemanticSegmentationAnnotationTable(
                sample_id=base_annotations[i].sample_id,
                segmentation_mask=annotation_create.segmentation_mask,
            )
            semantic_segmentation_annotations.append(db_semantic_segmentation)

    # Bulk save object detection annotations
    session.bulk_save_objects(object_detection_annotations)
    session.bulk_save_objects(instance_segmentation_annotations)
    session.bulk_save_objects(semantic_segmentation_annotations)

    # Commit everything
    session.commit()

    return [annotation.sample_id for annotation in base_annotations]
