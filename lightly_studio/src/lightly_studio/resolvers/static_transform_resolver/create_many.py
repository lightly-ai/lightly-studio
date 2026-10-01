"""Bulk-insert static transform edges for a recording."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.recording import RecordingTable
from lightly_studio.models.static_transform import StaticTransformCreate, StaticTransformTable


def create_many(
    session: Session,
    rows: Sequence[StaticTransformCreate],
) -> list[UUID]:
    """Bulk-insert static (``/tf_static``) transform edges for a bag.

    Args:
        session: The database session.
        rows: Transform edges to insert.

    Returns:
        The generated primary keys, in the same order as ``rows``.

    Raises:
        ValueError: If ``rows`` is empty, a row has an empty ``parent`` or ``child``, or a
            referenced ``recording_id`` has no ``recording`` row.
        sqlalchemy.exc.IntegrityError: If a row duplicates an existing
            ``(recording_id, parent, child)`` triple.
    """
    if not rows:
        raise ValueError("rows must be non-empty.")
    for row in rows:
        _validate_row(row)
    _check_recordings_exist(session=session, recording_ids={row.recording_id for row in rows})
    table_rows = [StaticTransformTable.model_validate(obj=row) for row in rows]
    session.bulk_save_objects(objects=table_rows)
    session.commit()
    return [row.static_transform_id for row in table_rows]


def _validate_row(row: StaticTransformCreate) -> None:
    if not row.parent.strip():
        raise ValueError("parent must be non-empty.")
    if not row.child.strip():
        raise ValueError("child must be non-empty.")


def _check_recordings_exist(session: Session, recording_ids: set[UUID]) -> None:
    found_ids = set(
        session.exec(
            select(RecordingTable.recording_id).where(
                col(RecordingTable.recording_id).in_(recording_ids)
            )
        ).all()
    )
    for recording_id in recording_ids - found_ids:
        raise ValueError(f"Recording with id {recording_id} not found.")
