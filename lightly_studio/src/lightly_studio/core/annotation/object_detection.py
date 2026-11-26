"""Interface for object detection annotations."""

from lightly_studio.core.annotation import Annotation
from lightly_studio.core.annotation.bounding_box_field import BoundingBoxField
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

    x = BoundingBoxField()
    """X coordinate (px) of the object detection bounding box."""
    y = BoundingBoxField()
    """Y coordinate (px) of the object detection bounding box."""
    width = BoundingBoxField()
    """Width (px) of the object detection bounding box."""
    height = BoundingBoxField()
    """Height (px) of the object detection bounding box."""

    def __init__(self, inner: ObjectDetectionAnnotationTable) -> None:
        """Initialize the Annotation.

        Args:
            inner: The ObjectDetectionAnnotationTable SQLAlchemy model instance.
        """
        if inner.annotation_base.annotation_type != AnnotationType.OBJECT_DETECTION:
            raise ValueError("Expected annotation type: object detection")

        super().__init__(inner.annotation_base)
        self.inner = inner
