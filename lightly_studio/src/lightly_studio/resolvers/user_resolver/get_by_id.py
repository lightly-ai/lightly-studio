"""Implementation of get user by ID resolver function."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from lightly_studio.models.user import UserTable


def get_by_id(session: Session, user_id: UUID) -> UserTable | None:
    """Retrieve a single user by ID."""
    return session.exec(select(UserTable).where(UserTable.user_id == user_id)).one_or_none()
