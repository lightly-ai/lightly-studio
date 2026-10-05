"""Agent tools that tag samples, run a diversity selection and show samples in the GUI."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from lightly_studio.agent import sample_source
from lightly_studio.agent.agent_tool import AgentContext, AgentTool
from lightly_studio.agent.ui_actions import SelectTagAction, ShowSamplesAction
from lightly_studio.resolvers import tag_resolver
from lightly_studio.sampling.sampling_config import EmbeddingDiversityStrategy, SamplingConfig
from lightly_studio.sampling.sampling_via_db import sampling_via_database

# The largest number of samples that the GUI grid is filtered to by sample ID.
_MAX_SHOWN_SAMPLES = 1000


class TagSamplesArgs(BaseModel):
    """Arguments of ``tag_samples``."""

    source: str = Field(description="The samples to tag. " + sample_source.SOURCE_DESCRIPTION)
    tag_name: str = Field(
        min_length=1,
        description="The tag to add the samples to. A missing tag is created.",
    )


class SelectDiverseArgs(BaseModel):
    """Arguments of ``select_diverse``."""

    n_samples: int = Field(gt=0, description="How many samples to select.")
    tag_name: str = Field(
        min_length=1,
        description="The name of the new tag for the selected samples. Must not exist yet.",
    )
    source: str = Field(
        default="all",
        description="The samples to select from. " + sample_source.SOURCE_DESCRIPTION,
    )


class ShowSamplesArgs(BaseModel):
    """Arguments of ``show_samples``."""

    source: str = Field(description="The samples to show. " + sample_source.SOURCE_DESCRIPTION)


def tag_samples(context: AgentContext, args: TagSamplesArgs) -> dict[str, Any]:
    """Add samples to a tag, and filter the GUI grid to that tag."""
    sample_ids = sample_source.resolve_source(context, args.source)
    tag = tag_resolver.get_or_create_sample_tag_by_name(
        session=context.session,
        collection_id=context.collection.collection_id,
        tag_name=args.tag_name.strip(),
    )
    tag_resolver.add_sample_ids_to_tag_id(
        session=context.session, tag_id=tag.tag_id, sample_ids=sample_ids
    )
    context.ui_actions.append(SelectTagAction(tag_id=tag.tag_id, tag_name=tag.name))
    return {"tag_name": tag.name, "tagged_count": len(sample_ids)}


def select_diverse(context: AgentContext, args: SelectDiverseArgs) -> dict[str, Any]:
    """Select samples that cover the embedding space well, and save them as a new tag."""
    tag_name = args.tag_name.strip()
    collection_id = context.collection.collection_id
    input_sample_ids = sample_source.resolve_source(context, args.source)
    config = SamplingConfig(
        collection_id=collection_id,
        n_samples_to_select=args.n_samples,
        sampling_result_tag_name=tag_name,
        strategies=[EmbeddingDiversityStrategy()],
    )
    # Raises `ValueError` if the tag name is taken.
    sampling_via_database(session=context.session, config=config, input_sample_ids=input_sample_ids)
    tag = tag_resolver.get_by_name(
        session=context.session, tag_name=tag_name, collection_id=collection_id
    )
    if tag is None:
        raise ValueError("The selection found no samples, so it created no tag.")
    selected_ids = tag_resolver.get_sample_ids_by_tag_id(session=context.session, tag_id=tag.tag_id)
    handle = context.result_store.put(collection_id=collection_id, sample_ids=selected_ids)
    context.ui_actions.append(SelectTagAction(tag_id=tag.tag_id, tag_name=tag.name))
    return {"tag_name": tag.name, "selected_count": len(selected_ids), "result": handle}


def show_samples(context: AgentContext, args: ShowSamplesArgs) -> dict[str, Any]:
    """Filter the GUI grid to a set of samples, without changing any data."""
    sample_ids = sample_source.resolve_source(context, args.source)[:_MAX_SHOWN_SAMPLES]
    context.ui_actions.append(ShowSamplesAction(sample_ids=sample_ids))
    return {"shown_count": len(sample_ids)}


TAG_TOOLS: list[AgentTool[Any]] = [
    AgentTool(
        name="tag_samples",
        description=(
            "Add samples to a tag. Creates the tag if it does not exist. The GUI then shows "
            "the tag."
        ),
        args_model=TagSamplesArgs,
        run=tag_samples,
    ),
    AgentTool(
        name="select_diverse",
        description=(
            "Select the most diverse samples, that is samples that cover the embedding space "
            "well, and save them as a new tag. Use it for requests such as 'the 128 most "
            "diverse images'. The GUI then shows the tag."
        ),
        args_model=SelectDiverseArgs,
        run=select_diverse,
    ),
    AgentTool(
        name="show_samples",
        description=(
            "Show samples in the GUI grid without tagging them. Use it when the user wants "
            "to see results but did not ask for a tag."
        ),
        args_model=ShowSamplesArgs,
        run=show_samples,
    ),
]
