"""v1 routes to read tags and to add them to samples or remove them from samples."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from lightly_studio.api.routes.api.status import HTTP_STATUS_NO_CONTENT
from lightly_studio.api.routes.api.v1 import collections
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.errors import NotFoundError
from lightly_studio.models.tag import TagSamplesBody, TagTable, TagView
from lightly_studio.resolvers import tag_resolver

tags_router = APIRouter()


@tags_router.get("/collections/{collection_id}/tags", response_model=TagView)
def v1_read_tag_by_name(session: SessionDep, collection_id: UUID, name: str) -> TagTable:
    """Get a tag of a collection by name."""
    tag = tag_resolver.get_by_name(session=session, tag_name=name, collection_id=collection_id)
    if tag is None:
        raise NotFoundError(f"Tag '{name}' not found.")
    return tag


@tags_router.post("/collections/{collection_id}/tags:add", status_code=HTTP_STATUS_NO_CONTENT)
def v1_add_tag_to_samples(session: SessionDep, collection_id: UUID, body: TagSamplesBody) -> None:
    """Add a tag to samples. Create the tag if it does not exist."""
    collections.get_collection(session=session, collection_id=collection_id)
    tag = tag_resolver.get_or_create_sample_tag_by_name(
        session=session, collection_id=collection_id, tag_name=body.tag_name
    )
    tag_resolver.add_sample_ids_to_tag_id(
        session=session, tag_id=tag.tag_id, sample_ids=body.sample_ids
    )


@tags_router.post("/collections/{collection_id}/tags:remove", status_code=HTTP_STATUS_NO_CONTENT)
def v1_remove_tag_from_samples(
    session: SessionDep, collection_id: UUID, body: TagSamplesBody
) -> None:
    """Remove a tag from samples. A tag that does not exist changes nothing."""
    tag = tag_resolver.get_by_name(
        session=session, tag_name=body.tag_name, collection_id=collection_id
    )
    if tag is not None:
        tag_resolver.remove_sample_ids_from_tag_id(
            session=session, tag_id=tag.tag_id, sample_ids=body.sample_ids
        )
