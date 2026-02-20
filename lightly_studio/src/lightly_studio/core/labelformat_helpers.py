"""Helper functions for the handling of labelformat classes."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal, Protocol
from uuid import UUID

from labelformat.model.binary_mask_segmentation import BinaryMaskSegmentation
from labelformat.model.bounding_box import BoundingBox, BoundingBoxFormat
from labelformat.model.category import Category
from labelformat.model.multipolygon import MultiPolygon
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import (
    AnnotationCreate,
    AnnotationType,
)
from lightly_studio.models.annotation_label import AnnotationLabelCreate
from lightly_studio.resolvers import annotation_label_resolver


class _LabelsWithCategories(Protocol):
    """Protocol for labelformat classes that have categories."""

    def get_categories(self) -> Iterable[Category]:
        """Get the categories of the labels."""
        ...


def get_segmentation_annotation_create(
    parent_sample_id: UUID,
    annotation_label_id: UUID,
    segmentation: MultiPolygon | BinaryMaskSegmentation,
    annotation_type: Literal[
        AnnotationType.INSTANCE_SEGMENTATION, AnnotationType.SEMANTIC_SEGMENTATION
    ] = AnnotationType.INSTANCE_SEGMENTATION,
) -> AnnotationCreate:
    """Get a AnnotationCreate instance for the provided labelformat instance segmentation.

    Args:
        parent_sample_id: ID of the parent sample of the annotation.
        annotation_label_id: ID of the label for the annotation.
        segmentation: Instance segmentation in labelformat.
        annotation_type: Instance or Semantic segmentation type.

    Returns:
        The AnnotationCreate instance for the provided details.
    """
    segmentation_rle: None | list[int] = None
    if isinstance(segmentation, MultiPolygon):
        box = segmentation.bounding_box().to_format(BoundingBoxFormat.XYWH)
    elif isinstance(segmentation, BinaryMaskSegmentation):
        box = segmentation.bounding_box.to_format(BoundingBoxFormat.XYWH)
        segmentation_rle = segmentation.get_rle()
    else:
        raise ValueError(f"Unsupported segmentation type: {type(segmentation)}")

    x, y, width, height = box
    return AnnotationCreate(
        parent_sample_id=parent_sample_id,
        annotation_label_id=annotation_label_id,
        annotation_type=annotation_type,
        x=int(x),
        y=int(y),
        width=int(width),
        height=int(height),
        segmentation_mask=segmentation_rle,
    )


def get_object_detection_annotation_create(
    parent_sample_id: UUID,
    annotation_label_id: UUID,
    box: BoundingBox,
    confidence: float | None = None,
) -> AnnotationCreate:
    """Get a AnnotationCreate instance for the provided labelformat object detection.

    Args:
        parent_sample_id: ID of the parent sample of the annotation.
        annotation_label_id: ID of the label for the annotation.
        box: Object detection box in labelformat.
        confidence: The confidence of the detection (indicating that it is a prediction).

    Returns:
        The AnnotationCreate instance for the provided details.
    """
    x, y, width, height = box.to_format(BoundingBoxFormat.XYWH)
    return AnnotationCreate(
        parent_sample_id=parent_sample_id,
        annotation_label_id=annotation_label_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
        x=int(x),
        y=int(y),
        width=int(width),
        height=int(height),
        confidence=confidence,
    )


def create_label_map(
    session: Session,
    dataset_id: UUID,
    input_labels: _LabelsWithCategories,
) -> dict[int, UUID]:
    """Create a mapping of category IDs to annotation label IDs.

    Args:
        session: The database session.
        dataset_id: The ID of the root collection the labels belong to.
        input_labels: The labelformat input containing the categories.
    """
    label_map = {}
    for category in input_labels.get_categories():
        # Use label if already exists
        label = annotation_label_resolver.get_by_label_name(
            session=session, dataset_id=dataset_id, label_name=category.name
        )
        if label is None:
            # Create new label
            label_create = AnnotationLabelCreate(
                dataset_id=dataset_id,
                annotation_label_name=category.name,
            )
            label = annotation_label_resolver.create(session=session, label=label_create)

        label_map[category.id] = label.annotation_label_id
    return label_map
