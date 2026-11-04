"""Load the dynamic transforms stored for a recording near a capture time."""

from __future__ import annotations

import bisect
from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session

from lightly_studio.core.mcap.reader import calibration
from lightly_studio.core.mcap.type_definitions import StaticTransform
from lightly_studio.models.dynamic_transform import DynamicTransformTable
from lightly_studio.resolvers import dynamic_transform_resolver


class DynamicTransformsByTime:
    """Dynamic edges sorted by capture time, to select the edges near many capture times."""

    def __init__(self, edges: Sequence[StaticTransform]) -> None:
        """Sorts the edges by capture time.

        Args:
            edges: The edges to select from, e.g. the result of
                ``load_dynamic_transforms_between``.
        """
        self._edges = sorted(edges, key=lambda edge: edge.timestamp_ns)
        self._timestamps_ns = [edge.timestamp_ns for edge in self._edges]

    def near(self, timestamp_ns: int) -> list[StaticTransform]:
        """Return the edges captured within ``DYNAMIC_TRANSFORM_WINDOW_NS`` of a time.

        Args:
            timestamp_ns: The capture time to look around, in nanoseconds.

        Returns:
            The edges in the window, sorted by capture time.
        """
        window_ns = calibration.DYNAMIC_TRANSFORM_WINDOW_NS
        start = bisect.bisect_left(self._timestamps_ns, max(timestamp_ns - window_ns, 0))
        end = bisect.bisect_right(self._timestamps_ns, timestamp_ns + window_ns)
        return self._edges[start:end]


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
    return load_dynamic_transforms_between(
        session=session,
        recording_id=recording_id,
        start_ns=max(timestamp_ns - window_ns, 0),
        end_ns=timestamp_ns + window_ns,
    )


def load_dynamic_transforms_between(
    session: Session,
    recording_id: UUID,
    start_ns: int,
    end_ns: int,
) -> list[StaticTransform] | None:
    """Return the dynamic edges stored in a range of capture times.

    Load the edges of many ticks once, then select the edges of each tick with
    ``DynamicTransformsByTime``.

    Args:
        session: The database session.
        recording_id: The recording the edges belong to.
        start_ns: The first capture time of the range, in nanoseconds.
        end_ns: The last capture time of the range, in nanoseconds.

    Returns:
        The edges captured in ``[start_ns, end_ns]``. An empty list means the
        recording was indexed and has no edge in that range. ``None`` means the
        recording has no stored dynamic transforms, so the caller reads them from the
        file.
    """
    rows = dynamic_transform_resolver.get_near(
        session=session, recording_id=recording_id, start_ns=start_ns, end_ns=end_ns
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
