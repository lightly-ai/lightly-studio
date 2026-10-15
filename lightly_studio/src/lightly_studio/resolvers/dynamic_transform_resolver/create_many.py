"""Bulk-insert dynamic transform edges for a recording."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.dynamic_transform import DynamicTransformCreate, DynamicTransformTable
from lightly_studio.models.recording import RecordingTable


def create_many(
    session: Session,
    rows: Sequence[DynamicTransformCreate],
) -> list[UUID]:
    """Bulk-insert dynamic (``/tf``) transform edges for a recording.

    Args:
        session: The database session.
        rows: Transform edges to insert. The same parent and child may repeat at
            different capture times.

    Returns:
        The generated primary keys, in the same order as ``rows``.

    Raises:
        ValueError: If ``rows`` is empty, a row has an empty ``parent`` or ``child``, or a
            referenced ``recording_id`` has no ``recording`` row.
    """
    if not rows:
        raise ValueError("rows must be non-empty.")
    for row in rows:
        _validate_row(row=row)
    _check_recordings_exist(session=session, recording_ids={row.recording_id for row in rows})
    table_rows = [DynamicTransformTable.model_validate(obj=row) for row in rows]
    session.bulk_save_objects(objects=table_rows)
    session.commit()
    return [row.dynamic_transform_id for row in table_rows]


def _validate_row(row: DynamicTransformCreate) -> None:
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
