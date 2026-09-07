"""This module defines the Embedding_Model model for the application."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class EmbeddingModelBase(SQLModel):
    """Base class for the EmbeddingModel.

    Attributes:
        name: The name identifying the embedding model within its dataset.
        embedding_dimension: The dimension of the embeddings the model produces.
        dataset_id: The dataset owning the embedding model.
        remote_embedder_url: The base URL of the remote embedding backend, if the model is
            served remotely.
        api_key: The bearer token sent to `remote_embedder_url`. It is a secret: it must never
            reach a response model, so a route returning an embedding model needs a view model
            that omits it. `repr=False` keeps it out of log lines that dump the row.
    """

    name: str
    embedding_dimension: int
    dataset_id: UUID = Field(foreign_key="dataset.dataset_id", index=True)
    remote_embedder_url: str | None = None
    api_key: str | None = Field(default=None, repr=False)


class EmbeddingModelCreate(EmbeddingModelBase):
    """Model used for creating an embedding model."""


class EmbeddingModelTable(EmbeddingModelBase, table=True):
    """This class defines the EmbeddingModel model."""

    __tablename__ = "embedding_model"
    __table_args__ = (UniqueConstraint("dataset_id", "name", name="unique_embedding_model_name"),)
    embedding_model_id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
