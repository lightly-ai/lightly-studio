"""Interface for classification annotations."""

from lightly_studio.core.annotation import Annotation
from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationType,
)


class ClassificationAnnotation(Annotation):
    """Class for classification annotations."""

    def __init__(self, annotation_base: AnnotationBaseTable) -> None:
        """Initialize the Annotation.

        Args:
            annotation_base: The AnnotationBaseTable SQLAlchemy model instance.
        """
        if annotation_base.annotation_type != AnnotationType.CLASSIFICATION:
            raise ValueError("Expected annotation type: classification")

        super().__init__(annotation_base)
