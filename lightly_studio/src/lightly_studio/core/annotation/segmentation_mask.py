"""Interface for segmentation mask annotations."""

from __future__ import annotations

from sqlmodel import col

from lightly_studio.core.annotation import Annotation
from lightly_studio.core.annotation.bounding_box_field import BoundingBoxField
from lightly_studio.core.db_field import DBField
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.annotation.segmentation import (
    SegmentationAnnotationTable,
)


class SegmentationMaskAnnotation(Annotation):
    """Class for segmentation mask annotations.

    The properties of the annotation are accessible as attributes of this class.

    ```python
    print(f"Annotation x/y coordinates: ({annotation.x},{annotation.y})")
    print(f"Annotation width and height: {annotation.width}x{annotation.height}"
    print(f"Annotation segmentation mask: {annotation.segmentation_mask}"
    ```

    """

    x = BoundingBoxField()
    """X coordinate (px) of the segmentation mask bounding box."""
    y = BoundingBoxField()
    """Y coordinate (px) of the segmentation mask bounding box."""
    width = BoundingBoxField()
    """Width (px) of the segmentation mask bounding box."""
    height = BoundingBoxField()
    """Height (px) of the segmentation mask bounding box."""
    segmentation_mask = DBField(col(SegmentationAnnotationTable.segmentation_mask))
    """Segmentation mask given as a run-length encoding."""

    def __init__(self, inner: SegmentationAnnotationTable) -> None:
        """Initialize the Annotation.

        Args:
            inner: The SegmentationAnnotationTable SQLAlchemy model instance.
        """
        if inner.annotation_base.annotation_type != AnnotationType.SEGMENTATION_MASK:
            raise ValueError("Expected annotation type: segmentation mask")

        super().__init__(inner.annotation_base)
        self.inner = inner
