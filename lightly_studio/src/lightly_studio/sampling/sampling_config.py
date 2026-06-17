"""Pydantic models for the Sampling configuration."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

AnnotationsClassName = str
AnnotationClassToTarget = dict[AnnotationsClassName, float]


class SamplingConfig(BaseModel):
    """Configuration for the sampling process."""

    collection_id: UUID
    n_samples_to_select: int
    sampling_result_tag_name: str
    strategies: Sequence[SamplingStrategy]


class SamplingStrategy(BaseModel):
    """Base class for sampling strategies."""

    strength: float = 1.0


class EmbeddingDiversityStrategy(SamplingStrategy):
    """Sampling strategy based on embedding diversity."""

    strategy_name: Literal["diversity"] = "diversity"
    embedding_model_name: str | None = None


class EmbeddingDeduplicationStrategy(SamplingStrategy):
    """Sampling strategy that removes near-duplicates based on embedding distance.

    Selects samples that are spread out in embedding space and stops selecting
    once the closest remaining sample would be nearer than
    ``stopping_condition_minimum_distance`` to the already selected samples.
    """

    strategy_name: Literal["deduplication"] = "deduplication"
    embedding_model_name: str | None = None
    stopping_condition_minimum_distance: float = Field(ge=0)


class EmbeddingSimilarityStrategy(SamplingStrategy):
    """Sampling strategy based on embedding similarity to a tagged query set."""

    strategy_name: Literal["similarity"] = "similarity"
    query_tag_name: str
    embedding_model_name: str | None = None


class MetadataWeightingStrategy(SamplingStrategy):
    """Sampling strategy based on metadata weighting."""

    strategy_name: Literal["weights"] = "weights"
    metadata_key: str


class AnnotationClassBalancingStrategy(SamplingStrategy):
    """Sampling strategy based on class balancing."""

    strategy_name: Literal["balance"] = "balance"
    target_distribution: AnnotationClassToTarget | Literal["uniform"] | Literal["input"]
    annotation_source_id: UUID | None = None
