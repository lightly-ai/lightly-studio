"""Helpers for sensor calibration resolver tests."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.recording import RecordingFormat
from lightly_studio.resolvers import recording_resolver
from tests.helpers_resolvers import create_collection

K = [500.0, 0.0, 320.0, 0.0, 500.0, 240.0, 0.0, 0.0, 1.0]


def create_recording(session: Session) -> UUID:
    """Create a dataset collection and an MCAP recording under it."""
    collection = create_collection(session=session)
    return recording_resolver.create(
        session=session,
        dataset_id=collection.dataset_id,
        uri="/bags/drive_001.mcap",
        format_=RecordingFormat.MCAP,
    )
