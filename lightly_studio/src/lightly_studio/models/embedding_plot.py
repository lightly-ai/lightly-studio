"""Disposable saved coordinates for a collection's embedding plot."""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import LargeBinary
from sqlmodel import Column, Field, SQLModel


class EmbeddingPlotTable(SQLModel, table=True):
    """One full plot per collection and embedding model.

    Arrow stores coordinates and sample IDs together. The write token will coordinate
    rebuilds with vector writes; it is independent of the dirty flag.
    IDs have no foreign keys because plots are disposable derived data.
    """

    __tablename__ = "embedding_plot"

    collection_id: UUID = Field(primary_key=True)
    embedding_model_id: UUID = Field(primary_key=True)
    is_dirty: bool = Field(default=True)
    write_token: UUID = Field(default_factory=uuid4)
    data: bytes = Field(default=b"", sa_column=Column(LargeBinary, nullable=False))
