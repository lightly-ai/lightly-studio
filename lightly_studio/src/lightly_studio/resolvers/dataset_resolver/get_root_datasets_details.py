"""Handler for database operations related to fetching root datasets with details."""

from __future__ import annotations

from sqlmodel import Session, col, func, select

from lightly_studio.models.dataset import DatasetDashboardView, DatasetTable
from lightly_studio.models.sample import SampleTable


def get_root_datasets_details(session: Session) -> list[DatasetDashboardView]:
    """Get root datasets with detailed metadata including sample counts."""
    # Get root datasets only. (parent_dataset_id is None)
    root_datasets = session.exec(
        select(DatasetTable).where(col(DatasetTable.parent_dataset_id).is_(None))
    ).all()

    result = []
    for dataset in root_datasets:
        # Count samples for this dataset.
        sample_count = (
            session.exec(
                select(func.count()).where(SampleTable.dataset_id == dataset.dataset_id)
            ).one()
            or 0
        )

        result.append(
            DatasetDashboardView(
                dataset_id=dataset.dataset_id,
                name=dataset.name,
                sample_type=dataset.sample_type,
                created_at=dataset.created_at,
                total_sample_count=sample_count,
                # TODO (Mihnea 12/25): replace this with the actual location
                #  once we have it stored in the dataset table
                dir_path_abs="/path/to/dataset",
            )
        )

    return result
