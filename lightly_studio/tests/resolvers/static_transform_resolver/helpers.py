"""Helpers for static transform resolver tests."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.recording import RecordingFormat
from lightly_studio.models.static_transform import StaticTransformCreate
from lightly_studio.resolvers import recording_resolver
from tests.helpers_resolvers import create_collection


def create_recording(session: Session) -> UUID:
    """Create a dataset collection and an MCAP recording under it."""
    collection = create_collection(session=session)
    return recording_resolver.create(
        session=session,
        dataset_id=collection.dataset_id,
        uri="/bags/drive_001.mcap",
        format_=RecordingFormat.MCAP,
    )


def create_edge(
    recording_id: UUID,
    parent: str = "livox_front_left",
    child: str = "Main_optical",
) -> StaticTransformCreate:
    """Build a StaticTransformCreate with a fixed identity-ish pose."""
    return StaticTransformCreate(
        recording_id=recording_id,
        parent=parent,
        child=child,
        qx=0.0,
        qy=0.0,
        qz=0.0,
        qw=1.0,
        tx=0.1,
        ty=0.2,
        tz=0.3,
    )
