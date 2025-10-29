"""Implementation of get dataset by name resolver function."""

from __future__ import annotations

from sqlmodel import Session, select

from lightly_studio.models.dataset import DatasetTable


def get_by_name(session: Session, name: str) -> DatasetTable | None:
    """Retrieve a single dataset by name."""
    return session.exec(select(DatasetTable).where(DatasetTable.name == name)).one_or_none()
