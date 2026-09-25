"""Serialize a PointCloud2 message as an Arrow IPC stream."""

from __future__ import annotations

import io
from collections.abc import Mapping

import numpy as np
import pyarrow as pa
from pyarrow import ipc

from lightly_studio.services.recording_service import (
    build_point_cloud_columns,
    build_point_cloud_schema,
    point_cloud_value,
    read_point_cloud_layout,
    read_point_cloud_xyz,
)
from lightly_studio.services.recording_service.point_cloud_types import (
    PointCloudFrameMetadata,
    PointCloudPayload,
)


def serialize_point_cloud(
    message: object, channel_id: int, topic: str, log_time_ns: int
) -> PointCloudPayload:
    """Decode a PointCloud2 message and serialize its points as an Arrow IPC stream.

    The x, y, and z coordinate fields are required. Optional intensity and RGB
    fields are decoded when present, and non-finite points are dropped. Frame
    metadata is attached to the Arrow schema.

    Args:
        message: A decoded PointCloud2 ROS message or an equivalent mapping.
        channel_id: The MCAP channel the message was read from.
        topic: The topic the message was published on.
        log_time_ns: The log time of the message in nanoseconds.

    Returns:
        The serialized point data with its log time.

    Raises:
        McapAccessError: If the message misses required fields or declares row or
            point dimensions that cannot form a valid point buffer.
    """
    layout, data, fields = read_point_cloud_layout.read_point_cloud_layout(message=message)
    xyz = read_point_cloud_xyz.read_point_cloud_xyz(data=data, fields=fields, layout=layout)
    valid = np.isfinite(xyz).all(axis=1)
    columns = build_point_cloud_columns.build_point_cloud_columns(
        data=data, fields=fields, layout=layout, xyz=xyz, valid=valid
    )
    frame_id = str(
        point_cloud_value.get_value(
            value=point_cloud_value.get_value(value=message, name="header"), name="frame_id"
        )
    )
    metadata = PointCloudFrameMetadata(
        channel_id=channel_id,
        topic=topic,
        log_time_ns=log_time_ns,
        frame_id=frame_id,
        source_point_count=layout.width * layout.height,
    )
    schema = build_point_cloud_schema.build_point_cloud_schema(
        columns=columns, metadata=metadata, xyz_valid=xyz[valid]
    )
    return _serialize_table(columns=columns, schema=schema, log_time_ns=log_time_ns)


def _serialize_table(
    columns: Mapping[str, pa.Array], schema: pa.Schema, log_time_ns: int
) -> PointCloudPayload:
    """Serialize the columns as an Arrow IPC stream payload."""
    table = pa.table(columns, schema=schema)
    buffer = io.BytesIO()
    with ipc.new_stream(buffer, schema) as writer:
        writer.write_table(table)
    return PointCloudPayload(data=buffer.getvalue(), log_time_ns=log_time_ns)
