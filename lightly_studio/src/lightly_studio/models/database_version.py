"""Model for tracking the LightlyStudio database schema version."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


class DatabaseVersionTable(SQLModel, table=True):
    """Stores the schema version expected by the running LightlyStudio package."""

    __tablename__ = "database_version"

    id: int = Field(default=1, primary_key=True)
    version: str = Field(index=True)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
