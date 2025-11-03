"""This module contains the User model for authentication."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class UserTable(SQLModel, table=True):
    """User model for database storage."""

    __tablename__ = "users"
    user_id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str  # Stored as Argon2 hash
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserView(SQLModel):
    """User model for API responses (no password)."""

    user_id: UUID
    email: str
    created_at: datetime
    updated_at: datetime
