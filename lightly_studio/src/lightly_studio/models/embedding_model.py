"""This module defines the Embedding_Model model for the application."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import UniqueConstraint
from sqlmodel import VARCHAR, Column, Field, SQLModel


class EmbeddingSpaceDescription(SQLModel):
    """Description of an embedding space."""

    name: str
    embedding_model_hash: str = Field(sa_column=Column(VARCHAR(128), nullable=False))
    embedding_dimension: int


class EmbeddingModelBase(EmbeddingSpaceDescription):
    """Base class for the EmbeddingModel."""

    dataset_id: UUID = Field(foreign_key="dataset.dataset_id", index=True)


class EmbeddingModelCreate(EmbeddingModelBase):
    """Model used for creating an embedding model."""


class EmbeddingModelTable(EmbeddingModelBase, table=True):
    """This class defines the EmbeddingModel model."""

    __tablename__ = "embedding_model"
    __table_args__ = (
        UniqueConstraint("dataset_id", "name", name="unique_embedding_model_name"),
        UniqueConstraint("dataset_id", "embedding_model_hash", name="unique_embedding_model_hash"),
    )
    embedding_model_id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
