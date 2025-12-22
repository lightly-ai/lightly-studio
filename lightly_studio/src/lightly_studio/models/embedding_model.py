"""This module defines the Embedding_Model model for the application."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlmodel import CHAR, Column, Field, SQLModel


class EmbeddingModelBase(SQLModel):
    """Base class for the EmbeddingModel."""

    name: str
    parameter_count_in_mb: int | None = None
    embedding_model_hash: str = Field(default="", sa_column=Column(CHAR(128)))
    embedding_dimension: int
    collection_id: UUID = Field(default=None, foreign_key="collection.collection_id")


class EmbeddingModelCreate(EmbeddingModelBase):
    """Model used for creating an embedding model."""


class EmbeddingModelTable(EmbeddingModelBase, table=True):
    """This class defines the EmbeddingModel model."""

    __tablename__ = "embedding_model"
    embedding_model_id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
