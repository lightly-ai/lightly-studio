"""Agent tools that prepare metadata and run a selection with any combination of strategies.

The ``strategies`` argument of ``run_selection`` is the ``Strategy`` union of the sampling
config. Its JSON schema documents every strategy for the model, so the agent can use a new
strategy of the union without a change here.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from lightly_studio.agent import distribution_tools, sample_source
from lightly_studio.agent.agent_tool import AgentContext, AgentTool
from lightly_studio.agent.ui_actions import SelectTagAction
from lightly_studio.resolvers import tag_resolver
from lightly_studio.resolvers.image_resolver.annotation_count_types import AnnotationCountMode
from lightly_studio.sampling.sampling_config import (
    AnnotationClassBalancingStrategy,
    MetadataBalancingStrategy,
    SamplingConfig,
    Strategy,
)
from lightly_studio.sampling.sampling_via_db import sampling_via_database
from lightly_studio.services import sampling_metadata
from lightly_studio.services.sampling_metadata import (
    MetadataComputation,
    SimilarityComputation,
    TypicalityComputation,
)


class ComputeMetadataArgs(BaseModel):
    """Arguments of ``compute_metadata``."""

    kind: Literal["typicality", "similarity"] = Field(
        description=(
            "'typicality': how representative each sample is of the collection; high for "
            "samples in dense regions, low for outliers. 'similarity': how similar each "
            "sample is to the samples of the query tag."
        )
    )
    metadata_name: str = Field(
        min_length=1, description="The metadata key to store the values in, e.g. 'typicality'."
    )
    query_tag: str | None = Field(
        default=None,
        description="Only for 'similarity': the name of the tag with the query samples.",
    )


class RunSelectionArgs(BaseModel):
    """Arguments of ``run_selection``."""

    n_samples: int = Field(gt=0, description="How many samples to select.")
    tag_name: str = Field(
        min_length=1,
        description="The name of the new tag for the selected samples. Must not exist yet.",
    )
    strategies: list[Strategy] = Field(
        min_length=1,
        description=(
            "The strategies to combine. The selection weights each strategy by its strength."
        ),
    )
    source: str = Field(
        default="all",
        description="The samples to select from. " + sample_source.SOURCE_DESCRIPTION,
    )


def compute_metadata(context: AgentContext, args: ComputeMetadataArgs) -> dict[str, Any]:
    """Compute typicality or similarity for every sample and store it as metadata."""
    computation = _to_computation(context=context, args=args)
    sampling_metadata.compute_metadata(
        session=context.session, collection=context.collection, computations=[computation]
    )
    return {"metadata_name": args.metadata_name, "computed": args.kind}


def run_selection(context: AgentContext, args: RunSelectionArgs) -> dict[str, Any]:
    """Select samples with a combination of strategies, and save them as a new tag."""
    tag_name = args.tag_name.strip()
    collection_id = context.collection.collection_id
    input_sample_ids = sample_source.resolve_source(context, args.source)
    config = SamplingConfig(
        collection_id=collection_id,
        n_samples_to_select=args.n_samples,
        sampling_result_tag_name=tag_name,
        strategies=args.strategies,
    )
    # Raises `ValueError` if the tag name is taken or a strategy names unknown data.
    sampling_via_database(session=context.session, config=config, input_sample_ids=input_sample_ids)
    tag = tag_resolver.get_by_name(
        session=context.session, tag_name=tag_name, collection_id=collection_id
    )
    if tag is None:
        raise ValueError("The selection found no samples, so it created no tag.")
    selected_ids = tag_resolver.get_sample_ids_by_tag_id(session=context.session, tag_id=tag.tag_id)
    handle = context.result_store.put(collection_id=collection_id, sample_ids=selected_ids)
    context.ui_actions.append(SelectTagAction(tag_id=tag.tag_id, tag_name=tag.name))
    result: dict[str, Any] = {
        "tag_name": tag.name,
        "selected_count": len(selected_ids),
        "result": handle,
        "strategies": [_describe_strategy(strategy=strategy) for strategy in args.strategies],
    }
    achieved = _get_achieved_distributions(
        context=context, sample_ids=selected_ids, strategies=args.strategies
    )
    if achieved:
        result["achieved_distributions"] = achieved
    return result


SELECTION_TOOLS: list[AgentTool[Any]] = [
    AgentTool(
        name="compute_metadata",
        description=(
            "Compute typicality or similarity for every sample of the collection and store "
            "it as numeric metadata. Run it before a selection that weights by that metadata."
        ),
        args_model=ComputeMetadataArgs,
        run=compute_metadata,
    ),
    AgentTool(
        name="run_selection",
        description=(
            "Select samples with one strategy or a combination of strategies, and save them "
            "as a new tag. Combine strategies for requests such as 'diverse but "
            "representative', 'balanced over weather' or 'similar to my night images but "
            "diverse'. The GUI then shows the tag. For metadata_balance and balance "
            "strategies, the result shows the distribution that the selection reached."
        ),
        args_model=RunSelectionArgs,
        run=run_selection,
    ),
]


def _to_computation(context: AgentContext, args: ComputeMetadataArgs) -> MetadataComputation:
    if args.kind == "typicality":
        return TypicalityComputation(kind="typicality", metadata_name=args.metadata_name)
    if args.query_tag is None:
        raise ValueError("A similarity computation needs a query_tag.")
    tag = tag_resolver.get_by_name(
        session=context.session,
        tag_name=args.query_tag.strip(),
        collection_id=context.collection.collection_id,
    )
    if tag is None:
        raise ValueError(f"There is no tag named {args.query_tag!r}.")
    return SimilarityComputation(
        kind="similarity", metadata_name=args.metadata_name, query_tag_id=tag.tag_id
    )


def _get_achieved_distributions(
    context: AgentContext, sample_ids: Sequence[UUID], strategies: Sequence[Strategy]
) -> dict[str, dict[str, Any]]:
    """Put the target of each balancing strategy next to the distribution of the selection.

    A metadata balancing strategy shows the shares of the samples per value, under its
    metadata key. A class balancing strategy shows the shares of the annotations per class,
    under ``annotation_classes``, because the balancing counts the annotations.
    """
    metadata_strategies = [
        strategy for strategy in strategies if isinstance(strategy, MetadataBalancingStrategy)
    ]
    achieved: dict[str, dict[str, Any]] = {}
    if metadata_strategies:
        values = distribution_tools.get_metadata_distributions(
            context=context,
            sample_ids=sample_ids,
            keys=[strategy.metadata_key for strategy in metadata_strategies],
        )
        for metadata_strategy in metadata_strategies:
            achieved[metadata_strategy.metadata_key] = {
                "target": metadata_strategy.target_distribution,
                "values": values[metadata_strategy.metadata_key],
            }
    for strategy in strategies:
        # A class balancing over one annotation source has no achieved distribution yet,
        # because the class counts include the annotations of all sources.
        if isinstance(strategy, AnnotationClassBalancingStrategy) and (
            strategy.annotation_source_id is None
        ):
            achieved["annotation_classes"] = {
                "target": strategy.target_distribution,
                "values": distribution_tools.get_annotation_class_distribution(
                    context=context, sample_ids=sample_ids, count_mode=AnnotationCountMode.OBJECTS
                ),
            }
    return achieved


def _describe_strategy(strategy: Strategy) -> str:
    """Describe a strategy in short, for example ``weights(typicality) x2``."""
    name = strategy.strategy_name
    target = getattr(strategy, "metadata_key", None) or getattr(strategy, "query_tag_name", None)
    target_text = f"({target})" if target else ""
    return f"{name}{target_text} x{strategy.strength:g}"
