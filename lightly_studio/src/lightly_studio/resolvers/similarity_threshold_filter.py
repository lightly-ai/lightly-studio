"""Mixin for filtering a query by a minimum similarity to a text embedding."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field, model_validator
from pydantic_core import PydanticCustomError
from sqlalchemy.orm import Mapped, aliased
from sqlmodel import col, select
from typing_extensions import Self

from lightly_studio.database import db_vector
from lightly_studio.models.collection_embedding_model import CollectionEmbeddingModelTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.type_definitions import QueryType


class SimilarityThresholdFilter(BaseModel):
    """Mixin that keeps only samples similar enough to a text embedding.

    The filter is active when ``min_similarity`` is set. Each sample is compared with its
    embedding from the default embedding model of its own collection, the same model as the
    similarity sort uses. Samples without such an embedding do not match.
    """

    text_embedding: list[float] | None = None
    min_similarity: float | None = Field(default=None, ge=-1.0, le=1.0)

    @model_validator(mode="after")
    def _validate_text_embedding(self) -> Self:  # noqa: N804
        if self.min_similarity is not None and not self.text_embedding:
            # Not a ValueError: its exception in the error context is not JSON-serializable.
            raise PydanticCustomError(
                "min_similarity_requires_text_embedding",
                "min_similarity requires text_embedding.",
            )
        return self

    def _apply_similarity_threshold_filter(
        self,
        query: QueryType,
        sample_id_column: Mapped[UUID],
    ) -> QueryType:
        """Keep rows whose sample similarity to ``text_embedding`` is ``>= min_similarity``."""
        if self.min_similarity is None:
            return query
        # Alias the tables so the subquery does not correlate with the outer query.
        embedding = aliased(SampleEmbeddingTable)
        sample = aliased(SampleTable)
        distance = db_vector.cosine_distance(embedding.embedding, self.text_embedding)
        similar_sample_ids = (
            select(embedding.sample_id)
            .join(sample, col(sample.sample_id) == col(embedding.sample_id))
            .join(
                CollectionEmbeddingModelTable,
                (col(CollectionEmbeddingModelTable.collection_id) == col(sample.collection_id))
                & (
                    col(CollectionEmbeddingModelTable.embedding_model_id)
                    == col(embedding.embedding_model_id)
                ),
            )
            .where(col(CollectionEmbeddingModelTable.is_default).is_(True))
            .where(distance <= 1.0 - self.min_similarity)
        )
        return query.where(col(sample_id_column).in_(similar_sample_ids))
