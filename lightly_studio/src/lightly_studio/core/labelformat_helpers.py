"""Helper functions for the handling of labelformat classes."""

from __future__ import annotations

import logging
import math
from collections.abc import Iterable
from typing import Protocol
from uuid import UUID

from labelformat.model.binary_mask_segmentation import BinaryMaskSegmentation
from labelformat.model.bounding_box import BoundingBox, BoundingBoxFormat
from labelformat.model.category import Category
from labelformat.model.multipolygon import MultiPolygon

from lightly_studio.models.annotation.annotation_base import (
    AnnotationCreate,
    AnnotationType,
)
from lightly_studio.models.annotation.polygon import MIN_VERTICES_PER_PART, Polygons
from lightly_studio.transport import active_transport

logger = logging.getLogger(__name__)


class _LabelsWithCategories(Protocol):
    """Protocol for labelformat classes that have categories."""

    def get_categories(self) -> Iterable[Category]:
        """Get the categories of the labels."""
        ...


def get_segmentation_annotation_create(
    parent_sample_id: UUID,
    annotation_label_id: UUID,
    segmentation: MultiPolygon | BinaryMaskSegmentation,
    object_track_id: UUID | None = None,
) -> AnnotationCreate:
    """Get a AnnotationCreate instance for the provided labelformat segmentation mask.

    Args:
        parent_sample_id: ID of the parent sample of the annotation.
        annotation_label_id: ID of the label for the annotation.
        segmentation: Instance segmentation in labelformat.
        object_track_id: The track ID of the object (indicating that it is part of a track).

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
        annotation_type=AnnotationType.SEGMENTATION_MASK,
        x=int(x),
        y=int(y),
        width=int(width),
        height=int(height),
        segmentation_mask=segmentation_rle,
        object_track_id=object_track_id,
    )


def get_instance_segmentation_annotation_create(
    parent_sample_id: UUID,
    annotation_label_id: UUID,
    segmentation: MultiPolygon | BinaryMaskSegmentation,
) -> AnnotationCreate | None:
    """Get an AnnotationCreate instance for an instance segmentation of an image.

    A `MultiPolygon` becomes a polygon annotation with its valid parts. A
    `BinaryMaskSegmentation` becomes a segmentation mask annotation.

    Args:
        parent_sample_id: ID of the parent sample of the annotation.
        annotation_label_id: ID of the label for the annotation.
        segmentation: Instance segmentation in labelformat.

    Returns:
        The AnnotationCreate instance, or None if a `MultiPolygon` has no valid part.
    """
    if isinstance(segmentation, MultiPolygon):
        return _get_polygon_annotation_create(
            parent_sample_id=parent_sample_id,
            annotation_label_id=annotation_label_id,
            multipolygon=segmentation,
        )
    return get_segmentation_annotation_create(
        parent_sample_id=parent_sample_id,
        annotation_label_id=annotation_label_id,
        segmentation=segmentation,
    )


def warn_skipped_polygons(count: int) -> None:
    """Log one warning for the polygon annotations that were skipped. Do nothing for 0."""
    if count == 0:
        return
    logger.warning(
        f"Skipped {count} polygon annotations without a valid part. "
        f"A valid part has at least {MIN_VERTICES_PER_PART} vertices and finite coordinates."
    )


def get_object_detection_annotation_create(
    parent_sample_id: UUID,
    annotation_label_id: UUID,
    box: BoundingBox,
    confidence: float | None = None,
    object_track_id: UUID | None = None,
) -> AnnotationCreate:
    """Get a AnnotationCreate instance for the provided labelformat object detection.

    Args:
        parent_sample_id: ID of the parent sample of the annotation.
        annotation_label_id: ID of the label for the annotation.
        box: Object detection box in labelformat.
        confidence: The confidence of the detection (indicating that it is a prediction).
        object_track_id: The track ID of the object (indicating that it is part of a track).

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
        object_track_id=object_track_id,
    )


# TODO(lukas 04/2026): change `root_collection_id` to `dataset_id`
def create_label_map(
    root_collection_id: UUID,
    input_labels: _LabelsWithCategories,
) -> dict[int, UUID]:
    """Create a mapping of category IDs to annotation label IDs.

    Args:
        root_collection_id: The ID of the root collection the labels belong to.
        input_labels: The labelformat input containing the categories.
    """
    transport = active_transport.get_transport()
    collection = transport.collections.get_by_id(collection_id=root_collection_id)
    if collection is None:
        raise ValueError(f"Collection {root_collection_id} doesn't exist")

    categories = list(input_labels.get_categories())
    labels = transport.annotations.get_or_create_labels(
        dataset_id=collection.dataset_id,
        label_names=[category.name for category in categories],
    )
    label_ids = {label.annotation_label_name: label.annotation_label_id for label in labels}
    return {category.id: label_ids[category.name] for category in categories}


def _get_polygon_annotation_create(
    parent_sample_id: UUID,
    annotation_label_id: UUID,
    multipolygon: MultiPolygon,
) -> AnnotationCreate | None:
    """Get a polygon AnnotationCreate with the valid parts, or None if no part is valid."""
    polygons = _valid_polygon_parts(multipolygon=multipolygon)
    if not polygons:
        return None
    return AnnotationCreate(
        parent_sample_id=parent_sample_id,
        annotation_label_id=annotation_label_id,
        annotation_type=AnnotationType.POLYGON,
        polygons=polygons,
    )


def _valid_polygon_parts(multipolygon: MultiPolygon) -> Polygons:
    """Get the parts of a multipolygon that have enough vertices and only finite coordinates."""
    return [
        part
        for part in multipolygon.polygons
        if len(part) >= MIN_VERTICES_PER_PART
        and all(math.isfinite(x) and math.isfinite(y) for x, y in part)
    ]
