"""Implementation of get dataset by ID resolver function."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from lightly_studio.models.dataset import DatasetTable

def get_by_parent_dataset_id(session: Session, dataset_id: UUID) -> DatasetTable | None:
    """Retrieve a single dataset by ID."""
    return session.exec(
        select(DatasetTable).where(DatasetTable.dataset_id == dataset_id)
    ).one_or_none()
