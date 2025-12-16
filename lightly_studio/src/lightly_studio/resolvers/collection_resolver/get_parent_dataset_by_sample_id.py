"""Retrieve the parent dataset for a given sample ID."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.sample import SampleTable


def get_parent_dataset_by_sample_id(session: Session, sample_id: UUID) -> CollectionTable | None:
    """Get parent dataset by sample ID.

    Args:
        session: Database session
        sample_id: ID of the sample for which to get the parent dataset

    Returns:
        Returns parent dataset
    """
    child = session.exec(
        select(CollectionTable).join(SampleTable).where(col(SampleTable.sample_id) == sample_id)
    ).one_or_none()

    return child.parent if child else None
