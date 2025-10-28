"""Handler for database operations related to datasets."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.dataset import DatasetCreate, DatasetTable


def create(session: Session, dataset: DatasetCreate) -> DatasetTable:
    """Create a new dataset in the database."""
    existing = get_by_name(session=session, name=dataset.name)
    if existing:
        raise ValueError(f"Dataset with name '{dataset.name}' already exists.")
    db_dataset = DatasetTable.model_validate(dataset)
    session.add(db_dataset)
    session.commit()
    session.refresh(db_dataset)
    return db_dataset


# TODO(Michal, 06/2025): Use Paginated struct instead of offset and limit
def get_all(session: Session, offset: int = 0, limit: int = 100) -> list[DatasetTable]:
    """Retrieve all datasets with pagination."""
    datasets = session.exec(
        select(DatasetTable)
        .order_by(col(DatasetTable.created_at).asc())
        .offset(offset)
        .limit(limit)
    ).all()
    return list(datasets) if datasets else []


def get_by_id(session: Session, dataset_id: UUID) -> DatasetTable | None:
    """Retrieve a single dataset by ID."""
    return session.exec(
        select(DatasetTable).where(DatasetTable.dataset_id == dataset_id)
    ).one_or_none()


def get_by_name(session: Session, name: str) -> DatasetTable | None:
    """Retrieve a single dataset by name."""
    return session.exec(select(DatasetTable).where(DatasetTable.name == name)).one_or_none()


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


def delete(session: Session, dataset_id: UUID) -> bool:
    """Delete a dataset."""
    dataset = get_by_id(session=session, dataset_id=dataset_id)
    if not dataset:
        return False

    session.delete(dataset)
    session.commit()
    return True
