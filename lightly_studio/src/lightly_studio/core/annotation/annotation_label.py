"""Annotation label."""

from uuid import UUID

from lightly_studio.models.annotation_label import AnnotationLabelTable


class AnnotationLabel:
    """Class for annotation label."""

    def __init__(self, inner: AnnotationLabelTable) -> None:
        """Initialize the AnnotationLabel."""
        self._inner = inner

    @property
    def id(self) -> UUID:
        """Annotation label ID."""
        return self._inner.annotation_label_id

    @property
    def name(self) -> str:
        """Annotation label name."""
        return self._inner.annotation_label_name

    def __repr__(self) -> str:
        """Return a string representation of the AnnotationLabel."""
        return f"AnnotationLabel(name='{self.name}', id={self.id})"
