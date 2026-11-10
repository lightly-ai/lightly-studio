"""This module defines the SchemaCompat model for the application."""

from __future__ import annotations

from sqlmodel import Field, SQLModel


class SchemaCompatTable(SQLModel, table=True):
    """One row that tells a client whether it can use the database.

    Each schema upgrade rewrites the row. A client that connects without
    migrating reads only this row, never ``alembic_version``.

    Attributes:
        id: Constant primary key, the table has exactly one row.
        oss_revision: The Alembic revision of the applied schema.
        min_client_version: The lowest lightly-studio version that can use the schema.
    """

    __tablename__ = "schema_compat"

    id: int = Field(default=1, primary_key=True)
    oss_revision: str
    min_client_version: str
