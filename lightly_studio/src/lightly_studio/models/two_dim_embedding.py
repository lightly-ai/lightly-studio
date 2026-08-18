"""Database table storing cached 2D embeddings."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import ARRAY, Float, Uuid
from sqlmodel import Column, Field, SQLModel


class TwoDimEmbeddingTable(SQLModel, table=True):
    """Cached 2D projection of a collection's embeddings, keyed by collection and model.

    ``sample_ids``, ``x`` and ``y`` are parallel arrays: entry ``i`` of each describes the
    same point. Storing the sample ids alongside the coordinates is what lets a cache hit
    answer a request without re-reading ``sample_embedding``.

    ``fingerprint`` identifies the set of samples the projection was computed from. A cache
    entry is stale as soon as the collection's fingerprint differs from the stored one.
    """

    __tablename__ = "two_dim_embeddings"

    collection_id: UUID = Field(primary_key=True, foreign_key="collection.collection_id")
    embedding_model_id: UUID = Field(
        primary_key=True, foreign_key="embedding_model.embedding_model_id"
    )
    fingerprint: str
    # Generic ARRAY (not postgresql.ARRAY) so the column compiles on DuckDB and PostgreSQL.
    sample_ids: list[UUID] = Field(sa_column=Column(ARRAY(Uuid)))
    x: list[float] = Field(sa_column=Column(ARRAY(Float)))
    y: list[float] = Field(sa_column=Column(ARRAY(Float)))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
