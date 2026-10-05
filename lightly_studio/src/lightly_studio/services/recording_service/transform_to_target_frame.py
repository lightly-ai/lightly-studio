"""Look up the transform from a source frame to a target frame of a recording."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from numpy.typing import NDArray

from lightly_studio.core.mcap.reader import McapFileReader
from lightly_studio.core.mcap.type_definitions import StaticTransform


def transform_to_target_frame(
    reader: McapFileReader,
    source_frame_id: str,
    target_frame_id: str | None,
    timestamp_ns: int,
    static_transforms: Sequence[StaticTransform],
) -> NDArray[np.float64] | None:
    """Return the transform from a source frame to the target frame at a time.

    Returns `None` if the data stays in the source frame, so a recording without
    transforms can still serve data in its own frame. The static edges come from
    the database. The dynamic edges are read from the recording at `timestamp_ns`.

    Args:
        reader: The reader of the recording.
        source_frame_id: The frame to map from, e.g. the frame of a sensor or a cuboid.
        target_frame_id: The frame to map to. `None` keeps the source frame.
        timestamp_ns: The capture time to look up the dynamic transforms at.
        static_transforms: The static edges stored for the recording.

    Returns:
        The 4x4 homogeneous transform that maps points from the source frame to the
        target frame, or `None` if the target frame is `None` or the source frame.

    Raises:
        TransformNotFoundError: If no chain of transforms connects the two frames.
        McapAccessError: If a message on the dynamic topic cannot be decoded.
    """
    if target_frame_id is None or target_frame_id == source_frame_id:
        return None
    return reader.get_transform_at(
        parent_frame_id=target_frame_id,
        child_frame_id=source_frame_id,
        timestamp_ns=timestamp_ns,
        static_transforms=static_transforms,
    )
