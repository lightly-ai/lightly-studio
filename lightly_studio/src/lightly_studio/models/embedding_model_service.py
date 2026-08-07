"""This module defines the EmbeddingModelService model for the application."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlmodel import VARCHAR, Column, Field, SQLModel


class EmbeddingModelServiceBase(SQLModel):
    """Base class for the EmbeddingModelService.

    Attributes:
        embedding_model_hash: Identifies the model the service serves. Matches
            ``embedding_model.embedding_model_hash``.
        serving_url: Base URL the browser calls to embed text and images.
    """

    embedding_model_hash: str = Field(
        sa_column=Column(VARCHAR(128), unique=True, index=True, nullable=False)
    )
    serving_url: str


class EmbeddingModelServiceTable(EmbeddingModelServiceBase, table=True):
    """Where the model behind an ``embedding_model_hash`` is served from.

    Keyed by model identity rather than by collection: the same model used across ten
    collections has ten ``embedding_model`` rows but one service row, so a hostname
    change is a single update.
    """

    __tablename__ = "embedding_model_service"
    embedding_model_service_id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
