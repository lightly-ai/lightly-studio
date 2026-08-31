"""This module defines the Embedding_Model model for the application."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class EmbeddingModelBase(SQLModel):
    """Base class for the EmbeddingModel."""

    name: str
    embedding_dimension: int
    dataset_id: UUID = Field(foreign_key="dataset.dataset_id", index=True)
    remote_embedder_url: str | None = None


class EmbeddingModelCreate(EmbeddingModelBase):
    """Model used for creating an embedding model."""


class EmbeddingModelTable(EmbeddingModelBase, table=True):
    """This class defines the EmbeddingModel model."""

    __tablename__ = "embedding_model"
    __table_args__ = (UniqueConstraint("dataset_id", "name", name="unique_embedding_model_name"),)
    embedding_model_id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
