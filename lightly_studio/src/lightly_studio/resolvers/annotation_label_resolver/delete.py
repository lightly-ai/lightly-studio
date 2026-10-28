"""Delete annotation label functionality."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.resolvers import evaluation_class_metric_resolver

from .get_by_id import get_by_id


def delete(session: Session, label_id: UUID) -> bool:
    """Delete an annotation label and its evaluation class metrics.

    The delete is not atomic. It commits twice: after the class metrics and after the label.

    Args:
        session (Session): The database session.
        label_id (UUID): The unique identifier of the annotation label.

    Returns:
        bool: True if the label was deleted, False if the label was not found.
    """
    label = get_by_id(session=session, label_id=label_id)
    if not label:
        return False

    evaluation_class_metric_resolver.delete_by_annotation_label_id(
        session=session, annotation_label_id=label_id
    )
    # DuckDB rejects the delete of the label in the transaction that deleted its class metrics.
    session.commit()
    session.delete(label)
    session.commit()
    return True
