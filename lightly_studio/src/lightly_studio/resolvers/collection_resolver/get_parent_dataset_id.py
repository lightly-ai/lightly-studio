"""Retrieve the parent dataset ID for a given dataset ID."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import aliased
from sqlmodel import Session, col, select

from lightly_studio.models.collection import CollectionTable

ParentDataset = aliased(CollectionTable)
ChildDataset = aliased(CollectionTable)


def get_parent_dataset_id(session: Session, dataset_id: UUID) -> CollectionTable | None:
    """Retrieve the parent dataset for a given dataset ID."""
    return session.exec(
        select(ParentDataset)
        .join(ChildDataset, col(ChildDataset.parent_dataset_id) == col(ParentDataset.dataset_id))
        .where(ChildDataset.dataset_id == dataset_id)
    ).one_or_none()
