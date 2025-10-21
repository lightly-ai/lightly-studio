"""Module for handling the update of annotation labels in the database."""

from __future__ import annotations

from typing import TypeVar
from uuid import UUID

from sqlmodel import Session, SQLModel

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
)
from lightly_studio.models.annotation.instance_segmentation import (
    InstanceSegmentationAnnotationTable,
)
from lightly_studio.models.annotation.links import AnnotationTagLinkTable
from lightly_studio.models.annotation.object_detection import ObjectDetectionAnnotationTable
from lightly_studio.models.annotation.semantic_segmentation import (
    SemanticSegmentationAnnotationTable,
)
from lightly_studio.resolvers import (
    annotation_resolver,
)

T = TypeVar("T", bound=SQLModel)


def update_annotation_label(
    session: Session, annotation_id: UUID, annotation_label_id: UUID
) -> AnnotationBaseTable:
    """Update the label of an annotation.

    Args:
        session: Database session for executing the operation.
        annotation_id: UUID of the annotation to update.
        annotation_label_id: UUID of the new label to assign to the annotation.

    Returns:
        The updated annotation with the new label assigned.

    Raises:
        ValueError: If the annotation is not found.
    """
    annotation = annotation_resolver.get_by_id(session, annotation_id)
    if not annotation:
        raise ValueError(f"Annotation with ID {annotation_id} not found.")

    # DuckDB has no "looking ahead" functionality for referenced tables.
    # We need to work around this by deleting the existing and re-inserting
    # Check https://duckdb.org/docs/stable/sql/indexes.html#over-eager-constraint-checking-in-foreign-keys

    # DuckDB has no "looking ahead" functionality for referenced tables and neither does it support cascading updates.  # noqa: E501
    # Herefore we need to delete and re-insert the affected rows.
    # more information can be found in the DuckDB documentation https://duckdb.org/docs/stable/sql/statements/create_table.html.
    try:
        # copy content
        annotation_copy = annotation.model_copy(update={"annotation_label_id": annotation_label_id})

        annotation_type = annotation_copy.annotation_type

        annotation_tags = [
            AnnotationTagLinkTable(
                annotation_id=annotation_copy.annotation_id,
                tag_id=tag.tag_id,
            )
            for tag in annotation.tags
        ]

        # we need to create a new annotation details before committing
        # because copy will be gone with the commit
        instance_segmentation = (
            InstanceSegmentationAnnotationTable(
                annotation_id=annotation_copy.annotation_id,
                segmentation_mask=annotation_copy.instance_segmentation_details.segmentation_mask,
                x=annotation_copy.instance_segmentation_details.x,
                y=annotation_copy.instance_segmentation_details.y,
                width=annotation_copy.instance_segmentation_details.width,
                height=annotation_copy.instance_segmentation_details.height,
            )
            if annotation_type == "instance_segmentation"
            and annotation_copy.instance_segmentation_details
            else None
        )

        object_detection = (
            ObjectDetectionAnnotationTable(
                annotation_id=annotation_copy.annotation_id,
                x=annotation_copy.object_detection_details.x,
                y=annotation_copy.object_detection_details.y,
                width=annotation_copy.object_detection_details.width,
                height=annotation_copy.object_detection_details.height,
            )
            if annotation_type == "object_detection" and annotation_copy.object_detection_details
            else None
        )

        semantic_segmentation = (
            SemanticSegmentationAnnotationTable(
                annotation_id=annotation_copy.annotation_id,
                segmentation_mask=annotation_copy.semantic_segmentation_details.segmentation_mask,
            )
            if annotation_type == "semantic_segmentation"
            and annotation_copy.semantic_segmentation_details
            else None
        )

        # delete
        annotation_resolver.delete_annotation(session, annotation.annotation_id)

        new_annotation = AnnotationBaseTable(
            annotation_id=annotation_copy.annotation_id,
            annotation_label_id=annotation_copy.annotation_label_id,
            annotation_type=annotation_copy.annotation_type,
            confidence=annotation_copy.confidence,
            created_at=annotation_copy.created_at,
            dataset_id=annotation_copy.dataset_id,
            sample_id=annotation_copy.sample_id,
        )

        session.add(new_annotation)

        if instance_segmentation:
            session.add(instance_segmentation)

        if object_detection:
            session.add(object_detection)

        if semantic_segmentation:
            session.add(semantic_segmentation)

        if annotation_tags:
            session.add_all(annotation_tags)

        session.commit()
        session.flush()

        return annotation_copy
    except Exception:
        # Explicit rollback to be safe, then re-raise the original error.
        session.rollback()
        raise

    return annotation
