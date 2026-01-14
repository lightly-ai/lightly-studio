"""Interface for semantic segmentation annotations."""

from __future__ import annotations

from sqlmodel import col

from lightly_studio.core.annotation import Annotation
from lightly_studio.core.db_field import DBField
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.annotation.semantic_segmentation import (
    SemanticSegmentationAnnotationTable,
)


class SemanticSegmentationAnnotation(Annotation):
    """Class for semantic segmentation annotations."""

    segmentation_mask = DBField(col(SemanticSegmentationAnnotationTable.segmentation_mask))

    def __init__(self, inner: SemanticSegmentationAnnotationTable) -> None:
        """Initialize the semantic segmentation annotation.

        Args:
            inner: The SemanticSegmentationAnnotationTable SQLAlchemy model instance.
        """
        if inner.annotation_base.annotation_type != AnnotationType.SEMANTIC_SEGMENTATION:
            raise ValueError("Expected annotation type: semantic segmentation")

        super().__init__(inner.annotation_base)
        self.inner = inner
