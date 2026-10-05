"""The agent tool that finds samples by their metadata values and annotation classes."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, Field

from lightly_studio.agent import sample_source
from lightly_studio.agent.agent_tool import AgentContext, AgentTool
from lightly_studio.resolvers import annotation_label_resolver, image_resolver
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.metadata_resolver.metadata_filter import MetadataFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter


class FindSamplesArgs(BaseModel):
    """Arguments of ``find_samples``."""

    metadata: list[MetadataFilter] = Field(
        default_factory=list,
        description=(
            "Conditions on metadata values. A sample must meet all of them. Use the keys and "
            "values from get_collection_overview. The operator 'in' takes a list of string or "
            "boolean values, for example {'key': 'weather', 'op': 'in', 'value': ['rain', "
            "'snow']}."
        ),
    )
    annotation_classes: list[str] = Field(
        default_factory=list,
        description=(
            "Names of annotation classes. A sample must have an annotation of at least one "
            "of them. For 'all of them', call the tool once per class with the earlier "
            "result as 'within'."
        ),
    )
    within: str | None = Field(
        default=None,
        description="Optional. Search only these samples. " + sample_source.SOURCE_DESCRIPTION,
    )


def find_samples(context: AgentContext, args: FindSamplesArgs) -> dict[str, Any]:
    """Find the samples whose metadata and annotations meet the conditions."""
    if not args.metadata and not args.annotation_classes:
        raise ValueError("Give at least one metadata condition or annotation class.")
    within = None if args.within is None else sample_source.resolve_source(context, args.within)
    sample_filter = SampleFilter(
        sample_ids=within,
        metadata_filters=args.metadata or None,
        annotations_filter=_annotations_filter(
            context=context, class_names=args.annotation_classes
        ),
    )
    sample_ids = image_resolver.get_sample_ids(
        session=context.session,
        collection_id=context.collection.collection_id,
        filters=ImageFilter(sample_filter=sample_filter),
    )
    handle = context.result_store.put(
        collection_id=context.collection.collection_id, sample_ids=sorted(sample_ids)
    )
    return {"result": handle, "count": len(sample_ids)}


FILTER_TOOLS: list[AgentTool[Any]] = [
    AgentTool(
        name="find_samples",
        description=(
            "Find the samples whose metadata values or annotation classes meet conditions, "
            "for example 'night images with a car'. Returns a result handle and the count. "
            "Use the handle as the source of other tools."
        ),
        args_model=FindSamplesArgs,
        run=find_samples,
    ),
]


def _annotations_filter(
    context: AgentContext, class_names: Sequence[str]
) -> AnnotationsFilter | None:
    """Build a filter for samples with any of the annotation classes.

    Raises:
        ValueError: If an annotation class does not exist.
    """
    if not class_names:
        return None
    label_ids = []
    for class_name in class_names:
        label = annotation_label_resolver.get_by_label_name(
            session=context.session,
            dataset_id=context.collection.dataset_id,
            label_name=class_name.strip(),
        )
        if label is None:
            raise ValueError(f"There is no annotation class named {class_name!r}.")
        label_ids.append(label.annotation_label_id)
    return AnnotationsFilter(annotation_label_ids=label_ids)
