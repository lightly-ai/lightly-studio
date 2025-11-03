"""Implementation of get user by email resolver function."""

from __future__ import annotations

from sqlmodel import Session, select

from lightly_studio.models.user import UserTable


def get_by_email(session: Session, email: str) -> UserTable | None:
    """Retrieve a single user by email."""
    return session.exec(select(UserTable).where(UserTable.email == email)).one_or_none()
