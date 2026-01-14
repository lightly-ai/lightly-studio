"""Interface for object detection annotations."""

from sqlmodel import col

from lightly_studio.core.annotation import Annotation
from lightly_studio.core.db_field import DBField
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.annotation.object_detection import ObjectDetectionAnnotationTable


class ObjectDetectionAnnotation(Annotation):
    """Class for object detection annotations.

    The properties of the annotation are accessible as attributes of this class.

    ```python
    print(f"Annotation x/y coordinates: ({annotation.x},{annotation.y})")
    print(f"Annotation width and height: {annotation.width}x{annotation.height}"
    ```
    """

    x = DBField(col(ObjectDetectionAnnotationTable.x))
    y = DBField(col(ObjectDetectionAnnotationTable.y))
    width = DBField(col(ObjectDetectionAnnotationTable.width))
    height = DBField(col(ObjectDetectionAnnotationTable.height))

    def __init__(self, inner: ObjectDetectionAnnotationTable) -> None:
        """Initialize the Annotation.

        Args:
            inner: The ObjectDetectionAnnotationTable SQLAlchemy model instance.
        """
        if inner.annotation_base.annotation_type != AnnotationType.OBJECT_DETECTION:
            raise ValueError("Expected annotation type: object detection")

        super().__init__(inner.annotation_base)
        self.inner = inner
