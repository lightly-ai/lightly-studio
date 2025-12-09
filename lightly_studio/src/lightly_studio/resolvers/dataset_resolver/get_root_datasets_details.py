"""Handler for database operations related to fetching root datasets with details."""

from __future__ import annotations

from sqlmodel import Session, col, func, select

from lightly_studio.models.dataset import DatasetDashboardView, DatasetTable
from lightly_studio.models.sample import SampleTable


def get_root_datasets_details(session: Session) -> list[DatasetDashboardView]:
    """Get root datasets with detailed metadata including sample counts."""
    datasets_query = (
        select( # type: ignore[call-overload]
            DatasetTable.dataset_id,
            DatasetTable.name,
            DatasetTable.sample_type,
            DatasetTable.created_at,
            func.count(SampleTable.dataset_id).label("sample_count"),
        )
        .outerjoin(SampleTable)
        .where(col(DatasetTable.parent_dataset_id).is_(None))
        .group_by(
            DatasetTable.dataset_id,
            DatasetTable.name,
            DatasetTable.sample_type,
            DatasetTable.created_at, # type: ignore[arg-type]
        )
        .order_by(DatasetTable.name)
    )

    return [
        DatasetDashboardView(
            dataset_id=row.dataset_id,
            name=row.name,
            sample_type=row.sample_type,
            created_at=row.created_at,
            total_sample_count=row.sample_count,
            # TODO (Mihnea 12/25): replace this with the actual location
            #  once we have it stored in the dataset table
            dir_path_abs="/path/to/dataset",
        )
        for row in session.exec(datasets_query).all()
    ]

