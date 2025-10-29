"""Implementation of get all datasets resolver function."""

from __future__ import annotations

from sqlmodel import Session, col, select

from lightly_studio.models.dataset import DatasetTable


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
