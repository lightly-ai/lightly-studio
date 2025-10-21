"""Pydantic models for the Selection configuration."""

from __future__ import annotations

from typing import Literal, Sequence
from uuid import UUID

from pydantic import BaseModel


class SelectionConfig(BaseModel):
    """Configuration for the selection process."""

    dataset_id: UUID
    n_samples_to_select: int
    selection_result_tag_name: str
    strategies: Sequence[SelectionStrategy]


class SelectionStrategy(BaseModel):
    """Base class for selection strategies."""

    strength: float = 1.0


class EmbeddingDiversityStrategy(SelectionStrategy):
    """Selection strategy based on embedding diversity."""

    strategy_name: Literal["diversity"] = "diversity"
    embedding_model_name: str | None


class MetadataWeightingStrategy(SelectionStrategy):
    """Selection strategy based on metadata weighting."""

    strategy_name: Literal["weights"] = "weights"
    metadata_key: str
