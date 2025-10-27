"""Handler for database operations related to datasets."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, func, select

from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers import dataset_resolver


def get_samples_count(session: Session, dataset_id: UUID) -> int:
    """Get all samples count."""
    dataset = dataset_resolver.get_by_id(session=session, dataset_id=dataset_id)
    if not dataset:
        raise ValueError(f"Dataset ID was not found '{dataset_id}'.")

    return (
        session.exec(
            select(func.count(SampleTable.sample_id)).where(
                SampleTable.dataset_id == dataset.dataset_id
            )
        ).one()
        or 0
    )
