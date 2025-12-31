"""Shared utilities for similarity search in resolvers."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, select

from lightly_studio.models.embedding_model import EmbeddingModelTable
from lightly_studio.models.sample_embedding import SampleEmbeddingTable


def get_distance_expression(
    session: Session,
    collection_id: UUID,
    text_embedding: list[float] | None,
) -> tuple[UUID | None, Any]:
    """Get distance expression for similarity search if text_embedding is provided.

    Returns a tuple of (embedding_model_id, distance_expr). Both are None if
    no text_embedding is provided or no embedding model exists for the collection.
    """
    if not text_embedding:
        return None, None

    embedding_model_id = session.exec(
        select(EmbeddingModelTable.embedding_model_id)
        .where(EmbeddingModelTable.collection_id == collection_id)
        .limit(1)
    ).first()

    if not embedding_model_id:
        return None, None

    distance_expr = func.list_cosine_distance(
        SampleEmbeddingTable.embedding,
        text_embedding,
    )
    return embedding_model_id, distance_expr


def distance_to_similarity(distance: float) -> float:
    """Convert cosine distance to similarity score."""
    return 1.0 - distance
