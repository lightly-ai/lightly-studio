"""Interface for semantic segmentation annotations."""

from __future__ import annotations

from sqlmodel import col

from lightly_studio.core.annotation import Annotation
from lightly_studio.core.db_field import DBField
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.annotation.segmentation import SegmentationAnnotationTable


class SemanticSegmentationAnnotation(Annotation):
    """Class for semantic segmentation annotations.

    The properties of the annotation are accessible as attributes of this class.

    ```python
    print(f"Annotation x/y coordinates: ({annotation.x},{annotation.y})")
    print(f"Annotation width and height: {annotation.width}x{annotation.height}")
    print(f"Annotation segmentation mask: {annotation.segmentation_mask}")
    ```

    """

    x = DBField(col(SegmentationAnnotationTable.x))
    """X coordinate (px) of the segmentation bounding box."""
    y = DBField(col(SegmentationAnnotationTable.y))
    """Y coordinate (px) of the segmentation bounding box."""
    width = DBField(col(SegmentationAnnotationTable.width))
    """Width (px) of the segmentation bounding box."""
    height = DBField(col(SegmentationAnnotationTable.height))
    """Height (px) of the segmentation bounding box."""
    segmentation_mask = DBField(col(SegmentationAnnotationTable.segmentation_mask))
    """Segmentation mask given as a run-length encoding."""

    def __init__(self, inner: SegmentationAnnotationTable) -> None:
        """Initialize the semantic segmentation annotation.

        Args:
            inner: The SegmentationAnnotationTable SQLAlchemy model instance.
        """
        if inner.annotation_base.annotation_type != AnnotationType.SEMANTIC_SEGMENTATION:
            raise ValueError("Expected annotation type: semantic segmentation")

        super().__init__(inner.annotation_base)
        self.inner = inner
