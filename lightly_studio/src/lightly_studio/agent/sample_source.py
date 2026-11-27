"""Turns the sample source that the model names into sample IDs.

Several tools work on "some samples". The model names them with one string:

- ``all``: every sample of the collection.
- ``selection``: the samples that the user selected in the GUI.
- ``tag:<name>``: the samples of a tag.
- ``result_<id>``: the samples of an earlier result handle.
"""

from __future__ import annotations

from uuid import UUID

from lightly_studio.agent.agent_tool import AgentContext
from lightly_studio.resolvers import image_resolver, tag_resolver

SOURCE_DESCRIPTION = (
    "Which samples to use: 'all' for the whole collection, 'selection' for the samples that "
    "the user selected in the GUI, 'tag:<name>' for the samples of a tag, or a result handle "
    "from an earlier tool call."
)

_TAG_PREFIX = "tag:"


def resolve_source(context: AgentContext, source: str) -> list[UUID]:
    """Get the sample IDs of a source.

    Args:
        context: The context of the turn.
        source: The source, in one of the forms of ``SOURCE_DESCRIPTION``.

    Returns:
        The sample IDs. A result handle keeps its result order.

    Raises:
        ValueError: If the source names nothing, or names no samples.
    """
    source = source.strip()
    collection_id = context.collection.collection_id
    if source == "all":
        sample_ids = sorted(
            image_resolver.get_sample_ids(session=context.session, collection_id=collection_id)
        )
    elif source == "selection":
        sample_ids = list(context.selected_sample_ids)
    elif source.startswith(_TAG_PREFIX):
        sample_ids = _get_tag_sample_ids(context=context, tag_name=source[len(_TAG_PREFIX) :])
    else:
        sample_ids = context.result_store.get(collection_id=collection_id, handle=source)
    if not sample_ids:
        raise ValueError(f"The source {source!r} contains no samples.")
    return sample_ids


def _get_tag_sample_ids(context: AgentContext, tag_name: str) -> list[UUID]:
    tag = tag_resolver.get_by_name(
        session=context.session,
        tag_name=tag_name.strip(),
        collection_id=context.collection.collection_id,
    )
    if tag is None:
        raise ValueError(f"There is no tag named {tag_name!r}.")
    return tag_resolver.get_sample_ids_by_tag_id(session=context.session, tag_id=tag.tag_id)
