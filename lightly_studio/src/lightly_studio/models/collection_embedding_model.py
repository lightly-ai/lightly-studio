"""This module defines the CollectionEmbeddingModel model for the application."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Field, SQLModel


class CollectionEmbeddingModelTable(SQLModel, table=True):
    """Link table: an embedding model used by a collection.

    One row per collection (the ``collection_id`` primary key enforces this). The row
    points at the ``embedding_model`` used whenever a caller does not name one explicitly,
    e.g. the 2D projection endpoints and similarity search. ``is_default`` flags that
    model as the collection's default.

    A partial unique index enforces at most one default per collection. It is Postgres-only
    (DuckDB cannot create partial indexes), so it lives in the migration rather than here,
    and ``_include_object`` in ``migrations/env.py`` keeps autogenerate from dropping it.
    """

    __tablename__ = "collection_embedding_model"

    collection_id: UUID = Field(foreign_key="collection.collection_id", primary_key=True)
    embedding_model_id: UUID = Field(foreign_key="embedding_model.embedding_model_id")
    is_default: bool = Field(default=True)
