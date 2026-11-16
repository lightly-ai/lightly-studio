"""Pydantic models for the Sampling configuration."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field

AnnotationsClassName = str
AnnotationClassToTarget = dict[AnnotationsClassName, float]

# Values of a boolean key can be named either as booleans or as their lowercase names.
MetadataValueName = str | bool
MetadataValueToTarget = dict[MetadataValueName, float]


class _SamplingStrategyBase(BaseModel):
    """Shared fields of the sampling strategies."""

    strength: float = 1.0


class EmbeddingDiversityStrategy(_SamplingStrategyBase):
    """Sampling strategy based on embedding diversity."""

    strategy_name: Literal["diversity"] = Field(default="diversity", frozen=True)
    embedding_model_name: str | None = None


class EmbeddingDeduplicationStrategy(_SamplingStrategyBase):
    """Sampling strategy that removes near-duplicates based on embedding distance.

    Selects samples that are spread out in embedding space and stops selecting
    once the closest remaining sample would be nearer than
    ``stopping_condition_minimum_distance`` to the already selected samples.
    """

    strategy_name: Literal["deduplication"] = Field(default="deduplication", frozen=True)
    embedding_model_name: str | None = None
    stopping_condition_minimum_distance: float = Field(ge=0)


class EmbeddingSimilarityStrategy(_SamplingStrategyBase):
    """Sampling strategy based on embedding similarity to a tagged query set."""

    strategy_name: Literal["similarity"] = Field(default="similarity", frozen=True)
    query_tag_name: str
    embedding_model_name: str | None = None


class MetadataWeightingStrategy(_SamplingStrategyBase):
    """Sampling strategy based on metadata weighting."""

    strategy_name: Literal["weights"] = Field(default="weights", frozen=True)
    metadata_key: str


class AnnotationClassBalancingStrategy(_SamplingStrategyBase):
    """Sampling strategy based on class balancing."""

    strategy_name: Literal["balance"] = Field(default="balance", frozen=True)
    target_distribution: AnnotationClassToTarget | Literal["uniform"] | Literal["input"]
    annotation_source_id: UUID | None = None


class MetadataBalancingStrategy(_SamplingStrategyBase):
    """Sampling strategy that balances the selection over one categorical metadata key.

    Balances a single ``string`` or ``boolean`` key over at most 100 values. Combine one
    strategy per key to balance several keys, each on its own rather than over the
    combinations of their values. Samples without a value for the key are unaffected but
    stay available for selection.

    An explicit target distribution names the values of a ``boolean`` key either as
    ``True`` and ``False`` or as the lowercase strings ``"true"`` and ``"false"``. It may
    give a target to only some values; the remaining values then share the target left
    to 1.0.
    """

    strategy_name: Literal["metadata_balance"] = Field(default="metadata_balance", frozen=True)
    metadata_key: str
    target_distribution: MetadataValueToTarget | Literal["uniform"] | Literal["input"]


class SubpartDiversityStrategy(_SamplingStrategyBase):
    """Sampling strategy based on diversity of annotation subparts (crops)."""

    strategy_name: Literal["subpart_diversity"] = Field(default="subpart_diversity", frozen=True)
    embedding_model_name: str | None = None
    annotation_source_id: UUID | None = None


Strategy = Annotated[
    AnnotationClassBalancingStrategy
    | EmbeddingDeduplicationStrategy
    | EmbeddingDiversityStrategy
    | EmbeddingSimilarityStrategy
    | MetadataBalancingStrategy
    | MetadataWeightingStrategy
    | SubpartDiversityStrategy,
    Field(discriminator="strategy_name"),
]


class SamplingConfig(BaseModel):
    """Configuration for the sampling process."""

    collection_id: UUID
    n_samples_to_select: int
    sampling_result_tag_name: str
    preselected_tag_name: str | None = None
    strategies: Sequence[Strategy]
    selected_sequence_length: int | None = Field(
        default=None,
        ge=2,
        description=(
            "Number of frames per selected sequence. None selects individual samples. "
            "When set, n_samples_to_select still counts frames and must be a multiple "
            "of this value. Only VIDEO_FRAME collections and diversity strategies "
            "support sequences."
        ),
    )
