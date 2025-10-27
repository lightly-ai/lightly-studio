"""Handler for database operations related to datasets."""

from __future__ import annotations

from sqlmodel import Session, func, select

from lightly_studio.models.dataset import DatasetTable, DatasetViewWithCount
from lightly_studio.models.sample import SampleTable


def get_dataset_details(session: Session, dataset: DatasetTable) -> DatasetViewWithCount:
    """Convert a DatasetTable to DatasetViewWithCount with computed sample count."""
    sample_count = (
        session.exec(
            select(func.count("*")).where(SampleTable.dataset_id == dataset.dataset_id)
        ).one()
        or 0
    )
    return DatasetViewWithCount(
        dataset_id=dataset.dataset_id,
        name=dataset.name,
        created_at=dataset.created_at,
        updated_at=dataset.updated_at,
        total_sample_count=sample_count,
    )
