"""Interface for instance segmentation annotations."""

from __future__ import annotations

from sqlmodel import col

from lightly_studio.core.annotation import Annotation
from lightly_studio.core.db_field import DBField
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.annotation.instance_segmentation import (
    InstanceSegmentationAnnotationTable,
)


class InstanceSegmentationAnnotation(Annotation):
    """Class for instance segmentation annotations.

    The properties of the annotation are accessible as attributes of this class.

    ```python
    print(f"Annotation x/y coordinates: ({annotation.x},{annotation.y})")
    print(f"Annotation width and height: {annotation.width}x{annotation.height}"
    print(f"Annotation segmentation mask: {annotation.segmentation_mask}"
    ```

    """

    x = DBField(col(InstanceSegmentationAnnotationTable.x))
    """X coordinate (px) of the instance bounding box."""
    y = DBField(col(InstanceSegmentationAnnotationTable.y))
    """Y coordinate (px) of the instance bounding box."""
    width = DBField(col(InstanceSegmentationAnnotationTable.width))
    """Width (px) of the instance bounding box."""
    height = DBField(col(InstanceSegmentationAnnotationTable.height))
    """Height (px) of the instance bounding box."""
    segmentation_mask = DBField(col(InstanceSegmentationAnnotationTable.segmentation_mask))
    """Segmentation mask of the instance bounding box given as a list of integers."""

    def __init__(self, inner: InstanceSegmentationAnnotationTable) -> None:
        """Initialize the Annotation.

        Args:
            inner: The InstanceSegmentationAnnotationTable SQLAlchemy model instance.
        """
        if inner.annotation_base.annotation_type != AnnotationType.INSTANCE_SEGMENTATION:
            raise ValueError("Expected annotation type: instance segmentation")

        super().__init__(inner.annotation_base)
        self.inner = inner
