"""Implementation of create_group_components resolver function."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Tuple
from uuid import UUID

from sqlmodel import Session
from typing_extensions import TypeAlias

from lightly_studio.models.collection import CollectionCreate, CollectionTable, SampleType
from lightly_studio.resolvers import collection_resolver

# Define a type alias for group component definitions as (component_name, component_type)
GroupComponentDefinition: TypeAlias = Tuple[str, SampleType]


def create_group_components(
    session: Session,
    parent_collection_id: UUID,
    components: Sequence[GroupComponentDefinition],
) -> dict[str, CollectionTable]:
    """Create group components as child collections of a parent group collection.

    Args:
        session: The database session.
        parent_collection_id: The ID of the parent collection. Must be of type GROUP.
        components: A sequence of tuples defining the group components to create, where each
            tuple contains the component name and its sample type.

    Returns:
        A dictionary mapping component names to their corresponding created CollectionTable objects.

    Raises:
        ValueError: If the parent collection does not exist, is not of type GROUP,
            if group components already exist for the parent, or if there are duplicate
            component names in the input.
    """
    # Validate parent collection
    parent = collection_resolver.get_by_id(session=session, collection_id=parent_collection_id)
    if not parent:
        raise ValueError(f"Parent collection with id '{parent_collection_id}' does not exist.")
    if parent.sample_type != SampleType.GROUP:
        raise ValueError("Can only create group components for collections of type GROUP.")

    # Check if group components already exist
    # Note: We might decide in the future to allow adding more components later.
    existing_components = collection_resolver.get_group_components(
        session=session, parent_collection_id=parent_collection_id
    )
    if existing_components:
        raise ValueError("Group components already exist for this parent collection.")

    # Create child collections for each group component
    seen_names = set()
    children = {}
    for idx, (component_name, component_type) in enumerate(components):
        # Check for duplicate component names
        if component_name in seen_names:
            raise ValueError(f"Duplicate component name '{component_name}' in group components.")
        seen_names.add(component_name)

        # Create child collection for the group component
        child_create = CollectionCreate(
            name=f"{parent.name}_comp_{idx}",
            parent_collection_id=parent.collection_id,
            sample_type=component_type,
            group_component_name=component_name,
            group_component_index=idx,
        )
        child_table = collection_resolver.create(session=session, collection=child_create)
        children[component_name] = child_table

    return children
