"""This module defines the ApiKey model for database-backed API key authentication."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel


class ApiKeyStatus(str, Enum):
    """Status of an API key."""

    ACTIVE = "active"
    REVOKED = "revoked"


class ApiKeyBase(SQLModel):
    """Base class for ApiKey model."""

    name: str = Field(description="Name or description for the API key")
    user_id: int = Field(index=True, description="ID of the user that owns this API key")


class ApiKeyCreate(ApiKeyBase):
    """Model used when creating an API key."""

    expires_at: datetime | None = Field(default=None)


class ApiKeyView(ApiKeyBase):
    """Model used when viewing API key information."""

    api_key_id: UUID
    created_at: datetime
    expires_at: datetime | None = None
    last_used_at: datetime | None = None
    status: ApiKeyStatus


class ApiKeyCreateResponse(ApiKeyView):
    """Model returned when an API key is created (includes raw secret key)."""

    key: str


class ApiKeyTable(ApiKeyBase, table=True):
    """This class defines the ApiKey model table in the database."""

    __tablename__ = "api_key"

    api_key_id: UUID = Field(default_factory=uuid4, primary_key=True)
    key_hash: str = Field(index=True, unique=True, description="SHA-256 hash of secret key")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), index=True, nullable=False),
    )
    expires_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    last_used_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    status: ApiKeyStatus = Field(default=ApiKeyStatus.ACTIVE, index=True)
