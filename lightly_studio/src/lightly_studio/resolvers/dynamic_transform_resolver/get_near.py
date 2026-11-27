"""Read dynamic transform edges near a capture time."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.dynamic_transform import DynamicTransformTable


def get_near(
    session: Session,
    recording_id: UUID,
    start_ns: int,
    end_ns: int,
) -> list[DynamicTransformTable]:
    """Return the edges of a recording whose capture time is in ``[start_ns, end_ns]``."""
    return list(
        session.exec(
            select(DynamicTransformTable).where(
                col(DynamicTransformTable.recording_id) == recording_id,
                col(DynamicTransformTable.timestamp_ns) >= start_ns,
                col(DynamicTransformTable.timestamp_ns) <= end_ns,
            )
        ).all()
    )


def has_any(session: Session, recording_id: UUID) -> bool:
    """Return whether the recording has any stored dynamic transform."""
    row_id = session.exec(
        select(DynamicTransformTable.dynamic_transform_id)
        .where(col(DynamicTransformTable.recording_id) == recording_id)
        .limit(1)
    ).first()
    return row_id is not None
