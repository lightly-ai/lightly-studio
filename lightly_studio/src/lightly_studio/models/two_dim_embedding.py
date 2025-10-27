"""Database table storing cached 2D embeddings."""

from __future__ import annotations

from sqlalchemy import ARRAY, Float
from sqlmodel import Column, Field, SQLModel


class TwoDimEmbeddingTable(SQLModel, table=True):
    """Persisted 2D embedding projection identified by a deterministic hash."""

    __tablename__ = "two_dim_embeddings"

    hash: str = Field(primary_key=True)
    x: list[float] = Field(sa_column=Column(ARRAY(Float)))
    y: list[float] = Field(sa_column=Column(ARRAY(Float)))
