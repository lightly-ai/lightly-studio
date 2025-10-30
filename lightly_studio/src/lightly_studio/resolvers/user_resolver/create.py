"""Implementation of create user resolver function."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.user import UserTable


def create(session: Session, email: str, hashed_password: str) -> UserTable:
    """Create a new user.

    Args:
        session: The database session.
        email: The user's email address.
        hashed_password: The pre-hashed password.

    Returns:
        The created user.
    """
    user = UserTable(email=email, hashed_password=hashed_password)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user