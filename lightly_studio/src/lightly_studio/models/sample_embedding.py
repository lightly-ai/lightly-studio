"""This module defines the SampleEmbedding model for the application."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import ARRAY, Float
from sqlmodel import Column, Field, Relationship, SQLModel

if TYPE_CHECKING:
    from lightly_studio.models.sample import SampleTable

else:
    SampleTable = object


class SampleEmbeddingBase(SQLModel):
    """Base class for the Embeddings used for Samples."""

    sample_embedding_id: UUID = Field(default_factory=uuid4, primary_key=True)

    sample_id: UUID = Field(foreign_key="samples.sample_id")

    embedding_model_id: UUID = Field(foreign_key="embedding_models.embedding_model_id")
    embedding: list[float] = Field(sa_column=Column(ARRAY(Float)))


class SampleEmbeddingCreate(SampleEmbeddingBase):
    """Sample class when inserting."""


class SampleEmbeddingTable(SampleEmbeddingBase, table=True):
    """This class defines the SampleEmbedding model."""

    __tablename__ = "sample_embeddings"
    sample: SampleTable = Relationship(back_populates="embeddings")
