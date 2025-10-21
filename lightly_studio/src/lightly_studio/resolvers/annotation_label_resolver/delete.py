"""Delete annotation label functionality."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from .get_by_id import get_by_id


def delete(session: Session, label_id: UUID) -> bool:
    """Delete an annotation label.

    Args:
        session (Session): The database session.
        label_id (UUID): The unique identifier of the annotation label.

    Returns:
        bool: True if the label was deleted, False if the label was not found.
    """
    label = get_by_id(session=session, label_id=label_id)
    if not label:
        return False

    session.delete(label)
    session.commit()
    return True
