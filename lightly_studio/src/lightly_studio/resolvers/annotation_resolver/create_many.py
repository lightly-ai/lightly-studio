"""Handler for database operations related to annotations."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationCreate,
    AnnotationType,
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
    instance segmentation, or semantic segmentation) in the annotation collection child of
    the provided parent collection.

    It is responsibility of the caller to ensure that all parent samples belong to the same
    collection with ID `parent_collection_id`. This function does not perform this check for
    performance reasons.

    Args:
        session: SQLAlchemy session for database operations.
        parent_collection_id: UUID of the parent collection.
        annotations: List of annotation objects to create.

    Returns:
        List of created annotation IDs.
    """
    # Step 1: Create all base annotations
    base_annotations = []
    object_detection_annotations = []
    instance_segmentation_annotations = []
    semantic_segmentation_annotations = []
    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=session, collection_id=parent_collection_id, sample_type=SampleType.ANNOTATION
    )

    sample_ids = sample_resolver.create_many(
        session=session,
        samples=[SampleCreate(collection_id=annotation_collection_id) for _ in annotations],
    )
    for annotation_create, sample_id in zip(annotations, sample_ids):
        # Create base annotation
        db_base_annotation = AnnotationBaseTable(
            sample_id=sample_id,
            annotation_label_id=annotation_create.annotation_label_id,
            annotation_type=annotation_create.annotation_type,
            confidence=annotation_create.confidence,
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
            x, y, width, height = _validate_bbox(
                annotation=annotation_create, kind=AnnotationType.OBJECT_DETECTION
            )

            db_object_detection = ObjectDetectionAnnotationTable(
                sample_id=base_annotations[i].sample_id,
                x=x,
                y=y,
                width=width,
                height=height,
            )
            object_detection_annotations.append(db_object_detection)

        # Create instance segmentation details
        elif base_annotations[i].annotation_type == "instance_segmentation":
            x, y, width, height = _validate_bbox(
                annotation=annotation_create, kind=AnnotationType.INSTANCE_SEGMENTATION
            )
            db_instance_segmentation = InstanceSegmentationAnnotationTable(
                sample_id=base_annotations[i].sample_id,
                segmentation_mask=annotation_create.segmentation_mask,
                x=x,
                y=y,
                width=width,
                height=height,
            )
            instance_segmentation_annotations.append(db_instance_segmentation)
        elif base_annotations[i].annotation_type == "semantic_segmentation":
            if not annotation_create.segmentation_mask:
                raise ValueError("missing segmentation_mask property for semantic_segmentation.")
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


def _validate_bbox(annotation: AnnotationCreate, kind: str) -> tuple[int, int, int, int]:
    if annotation.x is None or annotation.y is None:
        raise ValueError(f"Missing x or y properties for {kind}.")
    if annotation.width is None:
        raise ValueError(f"Missing width property for {kind}.")
    if annotation.height is None:
        raise ValueError(f"Missing height property for {kind}.")

    return (annotation.x, annotation.y, annotation.width, annotation.height)
