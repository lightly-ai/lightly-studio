"""Interface for polygon annotations."""

from __future__ import annotations

from lightly_studio.core.annotation import Annotation
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.annotation.polygon import PolygonAnnotationTable, Polygons


class PolygonAnnotation(Annotation):
    """Class for polygon annotations.

    The properties of the annotation are accessible as attributes of this class.

    ```python
    print(f"Annotation bounding box: ({annotation.x},{annotation.y})")
    print(f"Annotation width and height: {annotation.width}x{annotation.height}")
    print(f"Annotation polygon parts: {annotation.polygons}")
    ```

    The bounding box is derived from the vertices, so it is read-only.
    """

    def __init__(self, inner: PolygonAnnotationTable) -> None:
        """Initialize the Annotation.

        Args:
            inner: The PolygonAnnotationTable SQLAlchemy model instance.
        """
        if inner.annotation_base.annotation_type != AnnotationType.POLYGON:
            raise ValueError("Expected annotation type: polygon")

        super().__init__(inner.annotation_base)
        self.inner = inner

    @property
    def x(self) -> int:
        """X coordinate (px) of the polygon bounding box."""
        return self.inner.x

    @property
    def y(self) -> int:
        """Y coordinate (px) of the polygon bounding box."""
        return self.inner.y

    @property
    def width(self) -> int:
        """Width (px) of the polygon bounding box."""
        return self.inner.width

    @property
    def height(self) -> int:
        """Height (px) of the polygon bounding box."""
        return self.inner.height

    @property
    def polygons(self) -> Polygons:
        """Parts of the polygon, each a list of (x, y) vertices in pixels."""
        return self.inner.polygons
