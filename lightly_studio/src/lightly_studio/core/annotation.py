"""Interface for annotations."""

from typing import cast

from sqlalchemy.orm import object_session
from sqlmodel import Session, col

from lightly_studio.core.db_field import DBField, DBFieldOwner
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable


class Annotation(DBFieldOwner):
    """Class for annotation."""

    confidence = DBField(col(AnnotationBaseTable.confidence))
    # TODO(lukas 1/2026): type should be ideally (also) encoded in Python's type system.
    type = DBField(col(AnnotationBaseTable.annotation_type))
    label = DBField(col(AnnotationBaseTable.annotation_label))

    def __init__(self, inner: AnnotationBaseTable) -> None:
        """Initialize the Annotation.

        Args:
            inner: The AnnotationBaseTable SQLAlchemy model instance.
        """
        self.inner = inner

    def get_object_session(self) -> Session:
        """Get the database session for this annotation.

        Returns:
            The SQLModel session.

        Raises:
            RuntimeError: If no active session is found.
        """
        session = object_session(self.inner)
        if session is None:
            raise RuntimeError("No active session found for the annotation")
        # Cast from SQLAlchemy Session to SQLModel Session for mypy.
        return cast(Session, session)
