"""Model for tracking the LightlyStudio database schema version."""

from __future__ import annotations

from sqlmodel import Field, SQLModel


class DatabaseVersionTable(SQLModel, table=True):
    """Stores the schema version expected by the running LightlyStudio package."""

    __tablename__ = "database_version"

    version: str = Field(primary_key=True)
