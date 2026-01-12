"""Implementation of create_many function for groups."""

from __future__ import annotations

from collections.abc import Collection, Sequence
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.group import GroupTable, SampleGroupLinkTable
from lightly_studio.models.sample import SampleCreate, SampleTable
from lightly_studio.resolvers import collection_resolver, sample_resolver


def create_many(
    session: Session,
    collection_id: UUID,
    groups: Sequence[Collection[UUID]],
) -> list[UUID]:
    """Creates group samples.

    Args:
        session: The database session.
        collection_id: The ID of the group collection.
        groups: List of groups, where each group is defined by sample IDs of its components.
            The collections the samples belong to are validated to be components of the parent
            group collection. Missing components are allowed.

    Returns:
        A list of UUIDs of the added group samples.
    """
    # Validate that all required components are present in each group
    _validate_groups(session=session, collection_id=collection_id, groups=groups)

    # Create the group samples
    group_sample_ids = sample_resolver.create_many(
        session=session,
        samples=[SampleCreate(collection_id=collection_id) for _ in groups],
    )
    # Bulk create GroupTable entries using the generated sample_ids
    session.bulk_save_objects(
        objects=[GroupTable(sample_id=sample_id) for sample_id in group_sample_ids]
    )
    # Bulk create SampleGroupLinkTable entries
    session.bulk_save_objects(
        objects=[
            SampleGroupLinkTable(
                sample_id=sample_id,
                parent_sample_id=group_sample_id,
            )
            for group_sample_id, sample_ids in zip(group_sample_ids, groups)
            for sample_id in sample_ids
        ]
    )
    session.commit()
    return group_sample_ids


def _validate_groups(
    session: Session,
    collection_id: UUID,
    groups: Sequence[Collection[UUID]],
) -> None:
    """Checks that valid components are present in each group.

    Checks that for each group, the collection IDs of the samples match the expected
    child collection IDs defined for the group collection. Missing components are allowed.

    Args:
        session: The database session.
        collection_id: The ID of the group collection.
        groups: The groups to validate. Each group is defined by sample IDs it contains.

    Raises:
        ValueError: If any group contains invalid components.
    """
    components = collection_resolver.get_group_components(
        session=session, parent_collection_id=collection_id
    )
    expected_component_ids_set = {comp.collection_id for comp in components.values()}

    # Get sample_id to collection_id mapping
    all_sample_ids = {sid for sample_ids in groups for sid in sample_ids}
    statement = select(SampleTable.sample_id, SampleTable.collection_id).where(
        col(SampleTable.sample_id).in_(all_sample_ids)
    )
    results = session.exec(statement).all()
    sample_id_to_collection_id = dict(results)

    for sample_ids in groups:
        component_ids_in_group = [sample_id_to_collection_id[sid] for sid in sample_ids]
        component_ids_in_group_set = set(component_ids_in_group)
        if len(component_ids_in_group) != len(component_ids_in_group_set):
            raise ValueError(
                f"Duplicate group components found in group defined by sample IDs {sample_ids}."
            )
        if not component_ids_in_group_set.issubset(expected_component_ids_set):
            raise ValueError(
                f"Sample IDs {sample_ids} to create a group do not belong to allowed components. "
                f"Group component collection IDs: {expected_component_ids_set}, "
                f"but got the following, which is not a subset: {component_ids_in_group}."
            )
