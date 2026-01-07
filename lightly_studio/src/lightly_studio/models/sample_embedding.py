"""This module defines the SampleEmbedding model for the application."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import ARRAY, Float
from sqlmodel import Column, Field, Relationship, SQLModel

from lightly_studio.models.sample import SampleTable


class SampleEmbeddingBase(SQLModel):
    """Base class for the Embeddings used for Samples."""

    sample_id: UUID = Field(foreign_key="sample.sample_id", primary_key=True)
    embedding_model_id: UUID = Field(
        foreign_key="embedding_model.embedding_model_id", primary_key=True
    )
    embedding: list[float] = Field(sa_column=Column(ARRAY(Float)))


class SampleEmbeddingCreate(SampleEmbeddingBase):
    """Sample embedding class when inserting."""


class SampleEmbeddingTable(SampleEmbeddingBase, table=True):
    """This class defines the SampleEmbedding model."""

    __tablename__ = "sample_embedding"
    sample: SampleTable = Relationship(back_populates="embeddings")
