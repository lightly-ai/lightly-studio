"""Implementation of create dataset resolver function."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.dataset import DatasetCreate, DatasetTable
from lightly_studio.resolvers import dataset_resolver


def create(session: Session, dataset: DatasetCreate) -> DatasetTable:
    """Create a new dataset in the database."""
    existing = dataset_resolver.get_by_name(session=session, name=dataset.name)
    if existing:
        raise ValueError(f"Dataset with name '{dataset.name}' already exists.")
    db_dataset = DatasetTable.model_validate(dataset)
    session.add(db_dataset)
    session.commit()
    session.refresh(db_dataset)
    return db_dataset
