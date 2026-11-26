"""Interface for segmentation mask annotations."""

from __future__ import annotations

from collections.abc import Sequence

from lightly_studio.core.annotation import Annotation
from lightly_studio.core.annotation.bounding_box_field import BoundingBoxField
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.annotation.segmentation import (
    SegmentationAnnotationTable,
)
from lightly_studio.transport import active_transport


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

    def __init__(self, inner: SegmentationAnnotationTable) -> None:
        """Initialize the Annotation.

        Args:
            inner: The SegmentationAnnotationTable SQLAlchemy model instance.
        """
        if inner.annotation_base.annotation_type != AnnotationType.SEGMENTATION_MASK:
            raise ValueError("Expected annotation type: segmentation mask")

        super().__init__(inner.annotation_base)
        self.inner = inner

    @property
    def segmentation_mask(self) -> list[int] | None:
        """Segmentation mask given as a run-length encoding."""
        return self.inner.segmentation_mask

    @segmentation_mask.setter
    def segmentation_mask(self, value: Sequence[int]) -> None:
        active_transport.get_transport().annotations.update_segmentation_mask(
            annotation_id=self.annotation_base.sample_id, segmentation_mask=value
        )
