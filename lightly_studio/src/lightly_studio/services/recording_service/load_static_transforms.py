"""Load the static transforms stored for a recording."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.core.mcap.type_definitions import StaticTransform
from lightly_studio.models.static_transform import StaticTransformTable
from lightly_studio.resolvers import static_transform_resolver


def load_static_transforms(session: Session, recording_id: UUID) -> list[StaticTransform]:
    """Return the static transform edges stored for a recording.

    The edges are written when the recording is indexed. They have no timestamp,
    because a static transform is not matched to the query time.

    Args:
        session: The database session.
        recording_id: The recording the edges belong to.

    Returns:
        One transform per stored edge. An empty list means the recording has none.
    """
    return [
        _static_transform(row)
        for row in static_transform_resolver.get_all_by_recording_id(
            session=session, recording_id=recording_id
        )
    ]


def _static_transform(row: StaticTransformTable) -> StaticTransform:
    """Build a transform edge from a stored row."""
    return StaticTransform(
        parent_frame_id=row.parent,
        child_frame_id=row.child,
        translation=(row.tx, row.ty, row.tz),
        rotation=(row.qx, row.qy, row.qz, row.qw),
        timestamp_ns=0,
    )
