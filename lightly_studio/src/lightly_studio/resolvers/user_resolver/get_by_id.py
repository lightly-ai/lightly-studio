"""Query a user by ID."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.user import UserTable


def get_by_id(session: Session, user_id: int) -> UserTable | None:
    """Returns the user with the ID, or None if there is none.

    Args:
        session: Database session.
        user_id: The ID of the user.
    """
    return session.get(UserTable, user_id)
