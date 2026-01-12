"""Implementation of get_group_components_as_dict resolver function."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from lightly_studio.models.group import SampleGroupLinkTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers import collection_resolver, group_resolver


def get_group_components_as_dict(
    session: Session,
    sample_id: UUID,
) -> dict[str, SampleTable | None]:
    """Get components of a group sample.

    Args:
        session: The database session.
        sample_id: The ID of the group sample.

    Returns:
        A dictionary mapping component names to their corresponding SampleTable objects, or None
        if a component is missing.
    """
    group_sample = group_resolver.get_by_id(session=session, sample_id=sample_id)
    if group_sample is None:
        raise ValueError(f"Group sample with id '{sample_id}' does not exist.")

    # Fetch component collections
    component_collections = collection_resolver.get_group_components(
        session=session,
        parent_collection_id=group_sample.sample.collection_id,
    )
    # Note: Group components are guaranteed to be unique by name
    collection_id_to_component_name = {
        collection.collection_id: collection.group_component_name or ""
        for collection in component_collections.values()
    }

    # Get component samples
    statement = (
        select(SampleTable)
        .join(SampleGroupLinkTable)
        .where(
            SampleGroupLinkTable.sample_id == SampleTable.sample_id,
            SampleGroupLinkTable.parent_sample_id == sample_id,
        )
    )
    component_samples = session.exec(statement).all()

    # Map component samples to their group component names
    component_dct: dict[str, SampleTable | None] = {
        collection_id_to_component_name[component_sample.collection_id]: component_sample
        for component_sample in component_samples
    }
    # Fill in missing components with None
    for component_name in collection_id_to_component_name.values():
        if component_name not in component_dct:
            component_dct[component_name] = None

    return component_dct
