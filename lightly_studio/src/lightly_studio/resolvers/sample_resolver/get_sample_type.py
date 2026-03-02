"""Implementation of get_sample_type for sample resolver."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.models.sample import SampleTable


def get_sample_type(session: Session, sample_id: UUID) -> SampleType:
    """Retrieve the sample type for a given sample ID.

    Args:
        session: The database session.
        sample_id: The ID of the sample.

    Returns:
        The SampleType of the sample.

    Raises:
        ValueError: If the sample does not exist.
    """
    statement = (
        select(CollectionTable)
        .join(SampleTable, col(CollectionTable.collection_id) == col(SampleTable.collection_id))
        .where(SampleTable.sample_id == sample_id)
    )
    collection = session.exec(statement).one_or_none()
    if collection is None:
        raise ValueError(f"Sample with id '{sample_id}' does not exist.")
    return collection.sample_type
