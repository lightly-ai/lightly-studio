"""Implementation of update dataset resolver function."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.dataset import DatasetCreate, DatasetTable
from lightly_studio.resolvers.datasets_resolver.get_by_id import get_by_id


def update(session: Session, dataset_id: UUID, dataset_data: DatasetCreate) -> DatasetTable:
    """Update an existing dataset."""
    dataset = get_by_id(session=session, dataset_id=dataset_id)
    if not dataset:
        raise ValueError(f"Dataset ID was not found '{dataset_id}'.")

    dataset.name = dataset_data.name
    dataset.updated_at = datetime.now(timezone.utc)

    session.commit()
    session.refresh(dataset)
    return dataset
