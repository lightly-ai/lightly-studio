"""Check if export jobs reference collections."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.export_job import ExportJobTable


def exists_for_collection_ids(session: Session, collection_ids: Sequence[UUID]) -> bool:
    """Return True if an export job references one of the collections.

    Args:
        session: Database session.
        collection_ids: IDs of the collections.

    Returns:
        True if at least one export job references one of the collections.
    """
    export_key = session.exec(
        select(ExportJobTable.export_key)
        .where(col(ExportJobTable.collection_id).in_(collection_ids))
        .limit(1)
    ).first()
    return export_key is not None
