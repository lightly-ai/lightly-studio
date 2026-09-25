"""Build the Arrow schema of a serialized point cloud."""

from __future__ import annotations

import json
from collections.abc import Mapping

import numpy as np
import pyarrow as pa
from numpy.typing import NDArray

from lightly_studio.services.recording_service.point_cloud_types import PointCloudFrameMetadata


def build_point_cloud_schema(
    columns: Mapping[str, pa.Array],
    metadata: PointCloudFrameMetadata,
    xyz_valid: NDArray[np.float32],
) -> pa.Schema:
    """Build the Arrow schema with frame metadata and finite-point bounds.

    M is the number of finite points kept from the message.

    Args:
        columns: A map of column name to its Arrow float32 array.
        metadata: The frame-level metadata to attach to the schema.
        xyz_valid: The finite coordinates of shape (M, 3).

    Returns:
        The Arrow schema describing the columns and carrying the frame metadata.
    """
    bounds = (
        None
        if len(xyz_valid) == 0
        else {"min": xyz_valid.min(axis=0).tolist(), "max": xyz_valid.max(axis=0).tolist()}
    )
    return pa.schema(
        [pa.field(name, pa.float32(), nullable=False) for name in columns],
        metadata={
            "channel_id": str(metadata.channel_id).encode(),
            "topic": metadata.topic.encode(),
            "log_time_ns": str(metadata.log_time_ns).encode(),
            "frame_id": metadata.frame_id.encode(),
            "source_point_count": str(metadata.source_point_count).encode(),
            "point_count": str(len(xyz_valid)).encode(),
            "bounds": json.dumps(bounds, separators=(",", ":")).encode(),
            "coordinate_unit": b"meter",
        },
    )
