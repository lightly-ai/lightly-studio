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
    print(f"Annotation segmentation mask: {annotation.segmentation_mask}"
    ```

    """

    segmentation_mask = DBField(col(SegmentationAnnotationTable.segmentation_mask))
    """Segmentation mask as a list of integers."""

    def __init__(self, inner: SegmentationAnnotationTable) -> None:
        """Initialize the semantic segmentation annotation.

        Args:
            inner: The SegmentationAnnotationTable SQLAlchemy model instance.
        """
        if inner.annotation_base.annotation_type != AnnotationType.SEMANTIC_SEGMENTATION:
            raise ValueError("Expected annotation type: semantic segmentation")

        super().__init__(inner.annotation_base)
        self.inner = inner
