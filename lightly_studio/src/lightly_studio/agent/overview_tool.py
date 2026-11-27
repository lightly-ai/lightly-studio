"""The agent tools that describe the collection, so the model can choose the other tools.

The overview lists the facts that the selection and filter tools need: the tags, the
embedding models, the metadata keys with their values, and the annotation classes. A second,
lighter tool lists only the annotation classes, so the model can check whether a class matches
an object before it searches.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import Session

from lightly_studio.agent.agent_tool import AgentContext, AgentTool
from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.metadata import CATEGORICAL_TYPE_NAMES
from lightly_studio.resolvers import (
    collection_embedding_model_resolver,
    embedding_model_resolver,
    image_resolver,
    tag_resolver,
)
from lightly_studio.resolvers.image_resolver.annotation_count_types import AnnotationCountMode
from lightly_studio.resolvers.metadata_resolver.sample import (
    categorical_value_counts,
    get_metadata_info,
)

# The largest number of tags, metadata keys and annotation classes that the overview lists.
_MAX_LISTED_NAMES = 100

# The number of most frequent values that the overview lists for a categorical metadata key.
_MAX_LISTED_VALUES = 5


class GetCollectionOverviewArgs(BaseModel):
    """The overview takes no arguments."""


class ListAnnotationClassesArgs(BaseModel):
    """The list of annotation classes takes no arguments."""


def get_collection_overview(
    context: AgentContext, args: GetCollectionOverviewArgs
) -> dict[str, Any]:
    """Describe the collection: size, tags, embedding models, metadata and annotations."""
    del args
    session = context.session
    collection_id = context.collection.collection_id
    sample_count = image_resolver.get_all_by_collection_id(
        session=session, collection_id=collection_id, pagination=Paginated(offset=0, limit=1)
    ).total_count
    tags = tag_resolver.get_all_by_collection_id(
        session=session, collection_id=collection_id, limit=_MAX_LISTED_NAMES
    )
    return {
        "collection_name": context.collection.name,
        "sample_type": context.collection.sample_type.value,
        "sample_count": sample_count,
        "selected_sample_count": len(context.selected_sample_ids),
        "tags": [tag.name for tag in tags],
        "embedding_models": _get_embedding_models(session=session, collection_id=collection_id),
        "metadata": _get_metadata_facts(session=session, collection_id=collection_id),
        "annotation_classes": _get_annotation_classes(session=session, collection_id=collection_id),
    }


def list_annotation_classes(
    context: AgentContext, args: ListAnnotationClassesArgs
) -> dict[str, Any]:
    """List the annotation classes with the number of samples that have them."""
    del args
    return {
        "annotation_classes": _get_annotation_classes(
            session=context.session, collection_id=context.collection.collection_id
        )
    }


OVERVIEW_TOOLS: list[AgentTool[Any]] = [
    AgentTool(
        name="get_collection_overview",
        description=(
            "Get the facts about the collection: its size, the number of samples that the "
            "user selected in the GUI, its tags, its embedding models, its metadata keys "
            "with their type and values, and its annotation classes with the number of "
            "samples that have them. Call this first when a request depends on any of these "
            "facts, for example to choose selection strategies or filters."
        ),
        args_model=GetCollectionOverviewArgs,
        run=get_collection_overview,
    ),
    AgentTool(
        name="list_annotation_classes",
        description=(
            "List the annotation classes of the collection with the number of samples that "
            "have them, the most frequent first. Call it before you search for samples that "
            "show an object, to check whether an annotation class matches the object."
        ),
        args_model=ListAnnotationClassesArgs,
        run=list_annotation_classes,
    ),
]


def _get_embedding_models(session: Session, collection_id: UUID) -> list[dict[str, Any]]:
    default_id = collection_embedding_model_resolver.get_default_by_collection_id(
        session=session, collection_id=collection_id
    )
    model_ids = collection_embedding_model_resolver.get_all_by_collection_id(
        session=session, collection_id=collection_id
    )
    models = [
        embedding_model_resolver.get_by_id(session=session, embedding_model_id=model_id)
        for model_id in model_ids
    ]
    return [
        {"name": model.name, "is_default": model.embedding_model_id == default_id}
        for model in models
        if model is not None
    ]


def _get_metadata_facts(session: Session, collection_id: UUID) -> list[dict[str, Any]]:
    """List each metadata key with its type, its range or its most frequent values."""
    infos = get_metadata_info.get_metadata_info(session=session, collection_id=collection_id)
    infos = infos[:_MAX_LISTED_NAMES]
    value_counts = categorical_value_counts.get_metadata_value_counts(
        session=session,
        collection_id=collection_id,
        fields=[info.name for info in infos if info.type in CATEGORICAL_TYPE_NAMES],
        limit=_MAX_LISTED_VALUES,
    )
    facts = []
    for info in infos:
        fact: dict[str, Any] = {"key": info.name, "type": info.type}
        if info.min is not None:
            fact.update(min=info.min, max=info.max)
        if info.name in value_counts:
            fact["top_values"] = [
                {"value": count.value, "count": count.count}
                for count in value_counts[info.name].value_counts
            ]
        facts.append(fact)
    return facts


def _get_annotation_classes(session: Session, collection_id: UUID) -> list[dict[str, Any]]:
    """List the annotation classes, the most frequent first."""
    counts = image_resolver.count_image_annotations_by_collection(
        session=session, collection_id=collection_id, count_mode=AnnotationCountMode.SAMPLES
    )
    counts = sorted(counts, key=lambda count: count[2], reverse=True)[:_MAX_LISTED_NAMES]
    return [{"name": name, "sample_count": total} for name, _, total in counts]
