"""Pydantic models for the Selection configuration."""

from __future__ import annotations

from typing import Dict, Literal, Sequence
from uuid import UUID

from pydantic import BaseModel

AnnotationsClassName = str
AnnotationClassToTarget = Dict[AnnotationsClassName, float]


class SelectionConfig(BaseModel):
    """Configuration for the selection process."""

    collection_id: UUID
    n_samples_to_select: int
    selection_result_tag_name: str
    strategies: Sequence[SelectionStrategy]


class SelectionStrategy(BaseModel):
    """Base class for selection strategies."""

    strength: float = 1.0


class EmbeddingDiversityStrategy(SelectionStrategy):
    """Selection strategy based on embedding diversity."""

    strategy_name: Literal["diversity"] = "diversity"
    embedding_model_name: str | None = None


class MetadataWeightingStrategy(SelectionStrategy):
    """Selection strategy based on metadata weighting."""

    strategy_name: Literal["weights"] = "weights"
    metadata_key: str


class AnnotationClassBalancingStrategy(SelectionStrategy):
    """Selection strategy based on class balancing."""

    strategy_name: Literal["balance"] = "balance"
    target_distribution: AnnotationClassToTarget | Literal["uniform"] | Literal["input"]
    # TODO(Lukas 11/2025): Allow specifying the annotation task instead of merging annotations from
    # all tasks.
