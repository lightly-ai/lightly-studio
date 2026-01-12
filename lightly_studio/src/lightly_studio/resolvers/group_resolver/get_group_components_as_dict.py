"""TODO Implementation of get group components resolver function."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from lightly_studio.models.group import SampleGroupLinkTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers import collection_resolver, group_resolver


def get_group_components_as_dict(
    session: Session,
    sample_id: UUID,
) -> dict[str, SampleTable]:
    """TODO Get group components of a group sample."""
    group_sample = group_resolver.get_by_id(session=session, sample_id=sample_id)
    if group_sample is None:
        raise ValueError(f"Group sample with id '{sample_id}' does not exist.")

    # Fetch component collections
    component_collections = collection_resolver.get_group_components(
        session=session,
        parent_collection_id=group_sample.sample.collection_id,
    )
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

    print(component_samples)

    # Map component samples to their group component names
    return {
        collection_id_to_component_name[component_sample.collection_id]: component_sample
        for component_sample in component_samples
    }

    # comps = group_resolver.get_group_components_as_dict(
    #     session=db_session, sample_id=group_ids[0]
    # )
    # assert comps["front"].sample_id == front_images[0].sample_id
    # assert comps["back"].sample_id == back_images[0].sample_id

    # comps = group_resolver.get_group_components_as_dict(
    #     session=db_session, sample_id=group_ids[1]
    # )
    # assert comps["front"].sample_id == front_images[1].sample_id
    # assert comps["back"].sample_id == back_images[1].sample_id
