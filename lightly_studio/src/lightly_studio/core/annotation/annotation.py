"""Interface for annotations."""

from typing import Optional, cast

from sqlalchemy.orm import object_session
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable


class Annotation:
    """Class for annotation."""

    def __init__(self, annotation_base: AnnotationBaseTable) -> None:
        """Initialize the Annotation.

        Args:
            annotation_base: The AnnotationBaseTable SQLAlchemy model instance.
        """
        self.annotation_base = annotation_base

    def get_object_session(self) -> Session:
        """Get the database session for this annotation.

        Returns:
            The SQLModel session.

        Raises:
            RuntimeError: If no active session is found.
        """
        session = object_session(self.annotation_base)
        if session is None:
            raise RuntimeError("No active session found for the annotation")
        # Cast from SQLAlchemy Session to SQLModel Session for mypy.
        return cast(Session, session)

    @property
    def confidence(self) -> Optional[float]:
        """Annotation confidence."""
        return self.annotation_base.confidence

    @property
    def label(self) -> str:
        """Annotation label name."""
        return self.annotation_base.annotation_label.annotation_label_name
