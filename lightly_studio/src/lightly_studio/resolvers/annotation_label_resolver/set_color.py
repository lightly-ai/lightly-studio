"""Set the color of an annotation label."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation_label import AnnotationLabelTable

from .get_by_id import get_by_id


def set_color(
    session: Session, label_id: UUID, color: str | None, alpha: float | None
) -> AnnotationLabelTable | None:
    """Set or clear the color of an annotation label.

    Args:
        session (Session): The database session.
        label_id (UUID): The identifier of the annotation label.
        color (str | None): The new color. None clears it.
        alpha (float | None): The new opacity. None clears it.

    Returns:
        AnnotationLabelTable | None: The updated annotation label if it exists,
        otherwise None.
    """
    label = get_by_id(session=session, label_id=label_id)
    if not label:
        return None

    label.color = color
    label.alpha = alpha
    session.commit()
    session.refresh(label)
    return label
