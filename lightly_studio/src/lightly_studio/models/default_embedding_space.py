"""This module defines the DefaultEmbeddingSpace model for the application."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Field, SQLModel


class DefaultEmbeddingSpaceTable(SQLModel, table=True):
    """Link table: the default embedding space of a collection.

    One row per collection (the ``collection_id`` primary key enforces this). The
    embedding space is identified by the embedding model that produced it, so the row
    points at the ``embedding_model`` used whenever a caller does not name one
    explicitly, e.g. the 2D projection endpoints and similarity search.
    """

    __tablename__ = "default_embedding_space"

    collection_id: UUID = Field(foreign_key="collection.collection_id", primary_key=True)
    embedding_model_id: UUID = Field(foreign_key="embedding_model.embedding_model_id")
