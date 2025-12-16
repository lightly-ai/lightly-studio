"""Handler for database operations related to datasets."""

from __future__ import annotations

from sqlmodel import Session, func, select

from lightly_studio.models.collection import CollectionTable, CollectionViewWithCount
from lightly_studio.models.sample import SampleTable


def get_collection_details(session: Session, dataset: CollectionTable) -> CollectionViewWithCount:
    """Convert a CollectionTable to CollectionViewWithCount with computed sample count."""
    sample_count = (
        session.exec(
            select(func.count("*")).where(SampleTable.dataset_id == dataset.dataset_id)
        ).one()
        or 0
    )
    return CollectionViewWithCount(
        dataset_id=dataset.dataset_id,
        parent_dataset_id=dataset.parent_dataset_id,
        sample_type=dataset.sample_type,
        name=dataset.name,
        created_at=dataset.created_at,
        updated_at=dataset.updated_at,
        total_sample_count=sample_count,
    )
