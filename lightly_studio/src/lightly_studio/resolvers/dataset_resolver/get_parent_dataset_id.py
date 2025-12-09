"""Retrieve the parent dataset ID for a given dataset ID."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import aliased
from sqlmodel import Session, col, select

from lightly_studio.models.dataset import DatasetTable

ParentDataset = aliased(DatasetTable)
ChildDataset = aliased(DatasetTable)


def get_parent_dataset_id(session: Session, dataset_id: UUID) -> DatasetTable:
    """Retrieve the parent dataset for a given dataset ID."""
    result = session.exec(
        select(ParentDataset, ChildDataset)
        .join(ChildDataset, col(ChildDataset.parent_dataset_id) == col(ParentDataset.dataset_id))
        .where(ChildDataset.dataset_id == dataset_id)
    ).one_or_none()

    return result[0] if result else None
