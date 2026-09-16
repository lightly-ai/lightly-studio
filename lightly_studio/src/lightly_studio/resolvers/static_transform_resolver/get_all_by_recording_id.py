"""Read all static transform edges for an MCAP bag."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.static_transform import StaticTransformTable


def get_all_by_recording_id(session: Session, recording_id: UUID) -> list[StaticTransformTable]:
    """Return every static transform edge for a bag."""
    return list(
        session.exec(
            select(StaticTransformTable).where(
                col(StaticTransformTable.recording_id) == recording_id
            )
        ).all()
    )
