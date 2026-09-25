"""Serialize a PointCloud2 message as an Arrow IPC stream."""

from __future__ import annotations

import io
import json
from collections.abc import Mapping
from typing import Any, Literal

import numpy as np
import pyarrow as pa
from numpy.typing import NDArray
from pyarrow import ipc

from lightly_studio.core.mcap.errors import McapAccessError
from lightly_studio.services.recording_service import (
    normalize_point_cloud_intensity,
    point_cloud_value,
    read_point_cloud_colors,
    read_point_cloud_field,
)
from lightly_studio.services.recording_service.point_cloud_types import (
    SRGB_LINEAR_THRESHOLD,
    PointCloudLayout,
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
    layout, data, fields = _read_message_layout(message=message)
    xyz = _read_xyz(data=data, fields=fields, layout=layout)
    valid = np.isfinite(xyz).all(axis=1)
    columns = _build_columns(data=data, fields=fields, layout=layout, xyz=xyz, valid=valid)
    frame_id = str(
        point_cloud_value.get_value(
            value=point_cloud_value.get_value(value=message, name="header"), name="frame_id"
        )
    )
    schema = _build_schema(
        columns=columns,
        channel_id=channel_id,
        topic=topic,
        log_time_ns=log_time_ns,
        frame_id=frame_id,
        source_point_count=layout.width * layout.height,
        xyz_valid=xyz[valid],
    )
    return _serialize_table(columns=columns, schema=schema, log_time_ns=log_time_ns)


def _read_message_layout(
    message: object,
) -> tuple[PointCloudLayout, bytes, dict[str, object]]:
    """Read the byte layout, data buffer, and field map of a PointCloud2 message."""
    width = int(point_cloud_value.get_value(value=message, name="width"))
    height = int(point_cloud_value.get_value(value=message, name="height"))
    point_step = int(point_cloud_value.get_value(value=message, name="point_step"))
    row_step = int(point_cloud_value.get_value(value=message, name="row_step"))
    data = bytes(point_cloud_value.get_value(value=message, name="data"))
    fields = {
        str(point_cloud_value.get_value(value=field, name="name")): field
        for field in point_cloud_value.get_value(value=message, name="fields")
    }
    _validate_layout(
        width=width, height=height, point_step=point_step, row_step=row_step, data=data
    )
    _validate_required_fields(fields=fields)
    endian: Literal[">", "<"] = (
        ">" if bool(point_cloud_value.get_value(value=message, name="is_bigendian")) else "<"
    )
    layout = PointCloudLayout(
        width=width, height=height, point_step=point_step, row_step=row_step, endian=endian
    )
    return layout, data, fields


def _validate_layout(
    width: int, height: int, point_step: int, row_step: int, data: bytes
) -> None:
    """Reject dimensions that cannot form a valid strided view over the data."""
    fits_points = row_step >= width * point_step
    fits_rows = len(data) >= row_step * height
    if width < 0 or height < 0 or point_step <= 0 or not fits_points or not fits_rows:
        raise McapAccessError("Point cloud has invalid row or point data dimensions.")


def _validate_required_fields(fields: Mapping[str, object]) -> None:
    """Ensure the x, y, and z coordinate fields are present."""
    missing = sorted(name for name in ("x", "y", "z") if name not in fields)
    if missing:
        raise McapAccessError(f"Point cloud is missing required fields: {', '.join(missing)}.")


def _read_xyz(
    data: bytes, fields: Mapping[str, object], layout: PointCloudLayout
) -> NDArray[np.float32]:
    """Stack the x, y, and z fields into an (N, 3) float32 array."""
    points = [
        read_point_cloud_field.read_point_cloud_field(
            data=data, field=fields[name], layout=layout
        )
        for name in ("x", "y", "z")
    ]
    return np.column_stack(points).astype(np.float32)


def _build_columns(
    data: bytes,
    fields: Mapping[str, object],
    layout: PointCloudLayout,
    xyz: NDArray[np.float32],
    valid: NDArray[np.bool_],
) -> dict[str, pa.Array]:
    """Build the Arrow columns for coordinates, optional intensity, and color."""
    columns: dict[str, pa.Array] = {
        name: pa.array(xyz[valid, index], type=pa.float32())
        for index, name in enumerate(("x", "y", "z"))
    }
    if "intensity" in fields:
        intensity = read_point_cloud_field.read_point_cloud_field(
            data=data, field=fields["intensity"], layout=layout
        )
        columns["intensity"] = pa.array(
            normalize_point_cloud_intensity.normalize_point_cloud_intensity(
                values=intensity[valid]
            ),
            type=pa.float32(),
        )
    colors = read_point_cloud_colors.read_point_cloud_colors(
        data=data, fields=fields, layout=layout
    )
    if colors is not None:
        for index, name in enumerate(("r", "g", "b")):
            columns[name] = pa.array(_srgb_to_linear(channel=colors[valid, index]), type=pa.float32())
    return columns


def _srgb_to_linear(channel: NDArray[Any]) -> NDArray[np.float32]:
    """Convert an sRGB 0-255 color channel to linear RGB per the renderer contract."""
    srgb = channel.astype(np.float32) / 255.0
    linear = np.where(
        srgb <= SRGB_LINEAR_THRESHOLD, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4
    )
    return linear.astype(np.float32)


def _build_schema(
    columns: Mapping[str, pa.Array],
    channel_id: int,
    topic: str,
    log_time_ns: int,
    frame_id: str,
    source_point_count: int,
    xyz_valid: NDArray[np.float32],
) -> pa.Schema:
    """Build the Arrow schema with frame metadata and finite-point bounds."""
    bounds = (
        None
        if len(xyz_valid) == 0
        else {"min": xyz_valid.min(axis=0).tolist(), "max": xyz_valid.max(axis=0).tolist()}
    )
    return pa.schema(
        [pa.field(name, pa.float32(), nullable=False) for name in columns],
        metadata={
            "channel_id": str(channel_id).encode(),
            "topic": topic.encode(),
            "log_time_ns": str(log_time_ns).encode(),
            "frame_id": frame_id.encode(),
            "source_point_count": str(source_point_count).encode(),
            "point_count": str(len(xyz_valid)).encode(),
            "bounds": json.dumps(bounds, separators=(",", ":")).encode(),
            "coordinate_unit": b"meter",
        },
    )


def _serialize_table(
    columns: Mapping[str, pa.Array], schema: pa.Schema, log_time_ns: int
) -> PointCloudPayload:
    """Serialize the columns as an Arrow IPC stream payload."""
    table = pa.table(columns, schema=schema)
    buffer = io.BytesIO()
    with ipc.new_stream(buffer, schema) as writer:
        writer.write_table(table)
    return PointCloudPayload(data=buffer.getvalue(), log_time_ns=log_time_ns)
