"""Load the dynamic transforms stored for a recording near a capture time."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.core.mcap.reader import calibration
from lightly_studio.core.mcap.type_definitions import StaticTransform
from lightly_studio.models.dynamic_transform import DynamicTransformTable
from lightly_studio.resolvers import dynamic_transform_resolver


def load_dynamic_transforms_near(
    session: Session,
    recording_id: UUID,
    timestamp_ns: int,
) -> list[StaticTransform] | None:
    """Return the dynamic edges stored near a capture time.

    Each edge keeps its capture time, so the caller can pick the pose closest to
    ``timestamp_ns``.

    Args:
        session: The database session.
        recording_id: The recording the edges belong to.
        timestamp_ns: The capture time to look around, in nanoseconds.

    Returns:
        The edges captured within ``DYNAMIC_TRANSFORM_WINDOW_NS`` of ``timestamp_ns``.
        An empty list means the recording was indexed and has no edge in that window.
        ``None`` means the recording has no stored dynamic transforms, so the caller
        reads them from the file.
    """
    window_ns = calibration.DYNAMIC_TRANSFORM_WINDOW_NS
    rows = dynamic_transform_resolver.get_near(
        session=session,
        recording_id=recording_id,
        start_ns=max(timestamp_ns - window_ns, 0),
        end_ns=timestamp_ns + window_ns,
    )
    if rows:
        return [_dynamic_transform(row=row) for row in rows]
    if dynamic_transform_resolver.has_any(session=session, recording_id=recording_id):
        return []
    return None


def _dynamic_transform(row: DynamicTransformTable) -> StaticTransform:
    """Build a transform edge from a stored row."""
    return StaticTransform(
        parent_frame_id=row.parent,
        child_frame_id=row.child,
        translation=(row.tx, row.ty, row.tz),
        rotation=(row.qx, row.qy, row.qz, row.qw),
        timestamp_ns=row.timestamp_ns,
    )
