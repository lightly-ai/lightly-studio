"""Count images by status for a dataset."""
# isort: skip_file

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal
from uuid import UUID

from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from sqlmodel import Session, col, func, select


StatusField = Literal["status_metadata", "status_embeddings"]


def count_by_status(
    session: Session,
    dataset_id: UUID,
    status_field: StatusField = "status_embeddings",
    statuses: Iterable[str] | None = None,
) -> dict[str, int]:
    """Return counts of images grouped by status for a dataset.

    Args:
        session: Active database session.
        dataset_id: Dataset to count images for.
        status_field: Which status column to group by (`status_metadata` or `status_embeddings`).
        statuses: Optional iterable of statuses to filter by.

    Returns:
        Mapping of status -> count.
    """
    if status_field not in {"status_metadata", "status_embeddings"}:
        raise ValueError(f"Unknown status field: {status_field}")

    status_column = getattr(ImageTable, status_field)

    query = (
        select(status_column, func.count())
        .select_from(ImageTable)
        .join(ImageTable.sample)
        .where(SampleTable.dataset_id == dataset_id)
        .group_by(status_column)
    )

    if statuses:
        query = query.where(col(status_column).in_(list(statuses)))

    rows = session.exec(query).all()
    return dict(rows)
