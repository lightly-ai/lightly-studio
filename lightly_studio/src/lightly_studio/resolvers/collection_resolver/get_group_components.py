"""Implementation of get group components resolver function."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.resolvers import collection_resolver


def get_group_components(
    session: Session,
    parent_collection_id: UUID,
) -> dict[str, CollectionTable]:
    """Get group components of a parent group collection."""
    parent = collection_resolver.get_by_id(session=session, collection_id=parent_collection_id)
    if not parent:
        raise ValueError(f"Parent collection with id '{parent_collection_id}' does not exist.")
    if parent.sample_type != SampleType.GROUP:
        raise ValueError("Can only get group components for collections of type GROUP.")

    return {
        child.group_component_name: child
        for child in parent.children
        if child.group_component_name is not None
    }
