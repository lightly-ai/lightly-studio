"""Implementation of get_or_create_sample_tag_by_name function for tags."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.tag import TagCreate, TagTable
from lightly_studio.resolvers import tag_resolver


def get_or_create_sample_tag_by_name(
    session: Session,
    collection_id: UUID,
    tag_name: str,
) -> TagTable:
    """Get an existing sample tag by name or create a new one if it doesn't exist.

    Args:
        session: Database session for executing queries.
        collection_id: The collection ID to search/create the tag for.
        tag_name: Name of the tag to get or create.

    Returns:
        The existing or newly created sample tag.
    """
    existing_tag = tag_resolver.get_by_name(
        session=session, tag_name=tag_name, collection_id=collection_id
    )
    if existing_tag:
        return existing_tag

    new_tag = TagCreate(name=tag_name, collection_id=collection_id, kind="sample")
    return tag_resolver.create(session=session, tag=new_tag)
