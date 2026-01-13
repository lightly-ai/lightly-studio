"""TODO."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.models.group import SampleGroupLinkTable
from lightly_studio.models.sample import SampleTable


def get_sample_component_with_type(
    session: Session,
    sample_id: UUID,
    key: str,
) -> tuple[UUID | None, SampleType]:
    """TODO."""
    # Select a collection whose parent is the collection of the group sample
    # and whose group_component_name matches the provided key.
    comp_collection_statement = (
        select(CollectionTable)
        .join(
            SampleTable, col(CollectionTable.parent_collection_id) == col(SampleTable.collection_id)
        )
        .where(
            SampleTable.sample_id == sample_id,
            CollectionTable.group_component_name == key,
        )
    )
    comp_collection = session.exec(comp_collection_statement).one_or_none()
    if comp_collection is None:
        raise KeyError(
            f"Component with key '{key}' does not exist for group sample with id '{sample_id}'."
        )
    statement = (
        select(SampleGroupLinkTable.sample_id)
        .join(SampleTable, col(SampleGroupLinkTable.sample_id) == col(SampleTable.sample_id))
        .where(
            SampleGroupLinkTable.parent_sample_id == sample_id,
            SampleTable.collection_id == comp_collection.collection_id,
        )
    )
    comp_sample_id = session.exec(statement).one_or_none()

    return comp_sample_id, comp_collection.sample_type
