"""The component schema of an MCAP dataset, shared by all of its recordings."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session
from typing_extensions import TypeAlias

from lightly_studio.core.mcap.component import McapComponentSpec
from lightly_studio.models.collection import CollectionCreate, CollectionTable, SampleType
from lightly_studio.models.mcap_group_component_definition import McapDataType
from lightly_studio.resolvers import (
    collection_resolver,
    mcap_group_component_definition_resolver,
)

NamedDataType: TypeAlias = tuple[str, McapDataType]
"""The name of one component of an MCAP dataset and the kind of data it carries."""

GROUP_COLLECTION_SUFFIX = "_groups"
"""Appended to the name of a dataset to name the collection holding its groups."""


def create_components(
    session: Session,
    group_collection_id: UUID,
    components: Sequence[McapComponentSpec],
) -> None:
    """Create one component collection per component, with its MCAP definition.

    The channel and the frame of a component are left empty. They are read from the
    first recording that is indexed, with `McapComponent.update_mcap_definition`.

    Args:
        session: The database session.
        group_collection_id: The ID of the GROUP collection holding the components.
        components: The components of the dataset, in the order they are shown in.

    Raises:
        ValueError: If the GROUP collection already has components, or if two
            components have the same name.
    """
    component_collections = collection_resolver.create_group_components(
        session=session,
        parent_collection_id=group_collection_id,
        components=[(component.name, SampleType.MCAP) for component in components],
    )
    for component in components:
        mcap_group_component_definition_resolver.create(
            session=session,
            collection_id=component_collections[component.name].collection_id,
            mcap_data_type=component.mcap_data_type,
        )


def check_components_match(
    session: Session,
    group_collection_id: UUID,
    components: Sequence[McapComponentSpec],
    dataset_name: str,
) -> None:
    """Check that a dataset that exists has the components that were asked for.

    Args:
        session: The database session.
        group_collection_id: The ID of the GROUP collection holding the components.
        components: The components that were asked for, in order.
        dataset_name: The name of the dataset, for the error message.

    Raises:
        ValueError: If the dataset has other components than the ones asked for.
    """
    existing = get_components(session=session, group_collection_id=group_collection_id)
    requested = [(component.name, component.mcap_data_type) for component in components]
    if existing != requested:
        raise ValueError(
            f"Dataset with name '{dataset_name}' already exists with the components "
            f"{_format_components(components=existing)}, but "
            f"{_format_components(components=requested)} were requested."
        )


def get_components(session: Session, group_collection_id: UUID) -> list[NamedDataType]:
    """Get the components of an MCAP dataset, in the order they are shown in.

    Args:
        session: The database session.
        group_collection_id: The ID of the GROUP collection holding the components.

    Returns:
        The components as `(name, mcap_data_type)` pairs, ordered by their index.
        Components without an MCAP definition, e.g. classic image ones, are left out.
    """
    component_collections = collection_resolver.get_group_components(
        session=session, parent_collection_id=group_collection_id
    )
    mcap_data_types = {
        definition.collection_id: definition.mcap_data_type
        for definition in mcap_group_component_definition_resolver.get_all_by_group_collection_id(
            session=session, group_collection_id=group_collection_id
        )
    }
    indexed = [
        (
            _get_component_index(collection=collection),
            (component_name, mcap_data_types[collection.collection_id]),
        )
        for component_name, collection in component_collections.items()
        if collection.collection_id in mcap_data_types
    ]
    indexed.sort(key=lambda item: item[0])
    return [component for _, component in indexed]


def create_collections(session: Session, name: str) -> tuple[CollectionTable, CollectionTable]:
    """Create the root collection of an MCAP dataset and the one holding its groups.

    Args:
        session: The database session.
        name: The name of the dataset.

    Returns:
        The root collection, of type SEQUENCE, and its GROUP child collection.

    Raises:
        ValueError: If a dataset of that name exists.
    """
    root_collection = collection_resolver.create(
        session=session,
        collection=CollectionCreate(name=name, sample_type=SampleType.SEQUENCE),
    )
    group_collection = collection_resolver.create(
        session=session,
        collection=CollectionCreate(
            name=f"{name}{GROUP_COLLECTION_SUFFIX}",
            parent_collection_id=root_collection.collection_id,
            sample_type=SampleType.GROUP,
        ),
    )
    return root_collection, group_collection


def _get_component_index(collection: CollectionTable) -> int:
    """Return the position of a component collection in the schema of its groups."""
    definition = collection.group_component_definition
    # `get_group_components` only returns collections that have a definition.
    assert definition is not None
    return definition.group_component_index


def _format_components(components: Sequence[NamedDataType]) -> str:
    """Format components as `('name', 'data type')` pairs for an error message."""
    if not components:
        return "no components"
    return ", ".join(
        f"('{component_name}', '{mcap_data_type.value}')"
        for component_name, mcap_data_type in components
    )
