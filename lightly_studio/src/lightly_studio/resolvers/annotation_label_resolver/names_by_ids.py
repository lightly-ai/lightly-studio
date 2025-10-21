"""Get annotation label names by IDs functionality."""

from __future__ import annotations

from typing import Sequence
from uuid import UUID

from sqlmodel import Session

from .get_by_ids import get_by_ids


def names_by_ids(session: Session, ids: Sequence[UUID]) -> dict[str, str]:
    """Return a dictionary mapping annotation label IDs to their names.

    Args:
        session (Session): The database session used to query the labels.
        ids (Sequence[UUID]): A sequence of UUIDs of the annotation label IDs.

    Returns:
        dict[str, str]: A dictionary with string representations of the UUIDs
        and the values are the corresponding annotation label names.
    """
    labels = get_by_ids(session=session, ids=ids)
    return {str(label.annotation_label_id): label.annotation_label_name for label in labels}
