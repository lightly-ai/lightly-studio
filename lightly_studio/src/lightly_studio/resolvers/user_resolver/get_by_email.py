"""Query a user by email."""

from __future__ import annotations

from sqlmodel import Session, func, select

from lightly_studio.models.user import UserTable


def get_by_email(session: Session, email: str) -> UserTable | None:
    """Returns the user with the email, ignoring the letter case, or None if there is none.

    The auth service stores the email as the user typed it.

    Args:
        session: Database session.
        email: The email of the user.
    """
    return session.exec(
        select(UserTable).where(func.lower(UserTable.email) == email.lower())
    ).one_or_none()
