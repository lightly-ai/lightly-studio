"""Helper functions for the handling of labelformat classes."""

from __future__ import annotations

from uuid import UUID

from labelformat.model.binary_mask_segmentation import BinaryMaskSegmentation
from labelformat.model.bounding_box import BoundingBox, BoundingBoxFormat
from labelformat.model.multipolygon import MultiPolygon

from lightly_studio.models.annotation.annotation_base import AnnotationCreate, AnnotationType


def get_annotation_create_instance_segmentation(
    parent_sample_id: UUID,
    annotation_label_id: UUID,
    segmentation: MultiPolygon | BinaryMaskSegmentation,
) -> AnnotationCreate:
    """Get a AnnotationCreate instance for the provided labelformat instance segmentation.

    Args:
        parent_sample_id: ID of the parent sample of the annotation.
        annotation_label_id: ID od the label for the annotation.
        segmentation: Instance segmentation in labelformat.

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
        annotation_type=AnnotationType.INSTANCE_SEGMENTATION,
        x=int(x),
        y=int(y),
        width=int(width),
        height=int(height),
        segmentation_mask=segmentation_rle,
    )


def get_annotation_create_object_detection(
    parent_sample_id: UUID, annotation_label_id: UUID, box: BoundingBox
) -> AnnotationCreate:
    """Get a AnnotationCreate instance for the provided labelformat object detection.

    Args:
        parent_sample_id: ID of the parent sample of the annotation.
        annotation_label_id: ID od the label for the annotation.
        box: Object detection box in labelformat.

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
    )
