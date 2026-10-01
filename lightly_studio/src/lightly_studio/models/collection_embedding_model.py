"""This module defines the CollectionEmbeddingModel model for the application."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Field, SQLModel


class CollectionEmbeddingModelTable(SQLModel, table=True):
    """Link table: an embedding model used by a collection.

    One row per (collection, embedding model) pair, enforced by the composite
    ``(collection_id, embedding_model_id)`` primary key. A row records that the model is
    used by the collection, e.g. for the 2D projection endpoints and similarity search.
    ``is_default`` flags one of those models as the collection's default.

    A partial unique index enforces at most one default per collection, but only on
    Postgres. DuckDB cannot create partial indexes, so the index lives in the migration
    rather than here (``_include_object`` in ``migrations/env.py`` keeps autogenerate from
    dropping it). On DuckDB the invariant is not enforced at the database level; callers
    must maintain it.
    """

    __tablename__ = "collection_embedding_model"

    collection_id: UUID = Field(foreign_key="collection.collection_id", primary_key=True)
    embedding_model_id: UUID = Field(
        foreign_key="embedding_model.embedding_model_id", primary_key=True
    )
    is_default: bool = Field(default=False)
