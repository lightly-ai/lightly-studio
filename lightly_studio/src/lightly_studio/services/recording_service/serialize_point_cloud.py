"""Serialize a PointCloud2 message as an Arrow IPC stream."""

from __future__ import annotations

import io
import json
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
    PointCloudLayout,
    PointCloudPayload,
    SRGB_LINEAR_THRESHOLD,
)


def serialize_point_cloud(
    message: object, channel_id: int, topic: str, log_time_ns: int
) -> PointCloudPayload:
    """Decode PointCloud2 fields and serialize point rows with frame metadata."""
    width = int(point_cloud_value.get_value(message, "width"))
    height = int(point_cloud_value.get_value(message, "height"))
    point_step = int(point_cloud_value.get_value(message, "point_step"))
    row_step = int(point_cloud_value.get_value(message, "row_step"))
    data = bytes(point_cloud_value.get_value(message, "data"))
    fields = {
        str(point_cloud_value.get_value(field, "name")): field
        for field in point_cloud_value.get_value(message, "fields")
    }
    required = {name for name in ("x", "y", "z") if name not in fields}
    if required:
        missing = ", ".join(sorted(required))
        raise McapAccessError(f"Point cloud is missing required fields: {missing}.")
    if point_step <= 0 or len(data) < row_step * height:
        raise McapAccessError("Point cloud has invalid row or point data dimensions.")
    endian: Literal[">", "<"] = ">" if bool(
        point_cloud_value.get_value(message, "is_bigendian")
    ) else "<"
    layout = PointCloudLayout(
        width=width, height=height, point_step=point_step, row_step=row_step, endian=endian
    )
    points: dict[str, NDArray[Any]] = {
        name: read_point_cloud_field.read_point_cloud_field(data, fields[name], layout)
        for name in ("x", "y", "z")
    }
    source_point_count = width * height
    xyz = np.column_stack((points["x"], points["y"], points["z"])).astype(np.float32)
    valid = np.isfinite(xyz).all(axis=1)
    columns: dict[str, pa.Array] = {
        name: pa.array(xyz[valid, index], type=pa.float32())
        for index, name in enumerate(("x", "y", "z"))
    }
    if "intensity" in fields:
        intensity = read_point_cloud_field.read_point_cloud_field(
            data, fields["intensity"], layout
        )
        columns["intensity"] = pa.array(
            normalize_point_cloud_intensity.normalize_point_cloud_intensity(intensity[valid]),
            type=pa.float32(),
        )
    colors = read_point_cloud_colors.read_point_cloud_colors(data, fields, layout)
    if colors is not None:
        for index, name in enumerate(("r", "g", "b")):
            # PointCloud2 RGB fields are sRGB; the renderer contract uses linear RGB.
            srgb = colors[valid, index].astype(np.float32) / 255.0
            columns[name] = pa.array(
                np.where(
                    srgb <= SRGB_LINEAR_THRESHOLD,
                    srgb / 12.92,
                    ((srgb + 0.055) / 1.055) ** 2.4,
                ),
                type=pa.float32(),
            )
    xyz_valid = xyz[valid]
    bounds = (
        None
        if len(xyz_valid) == 0
        else {"min": xyz_valid.min(axis=0).tolist(), "max": xyz_valid.max(axis=0).tolist()}
    )
    frame_id = str(
        point_cloud_value.get_value(point_cloud_value.get_value(message, "header"), "frame_id")
    )
    schema = pa.schema(
        [pa.field(name, pa.float32(), nullable=False) for name in columns],
        metadata={
            "channel_id": str(channel_id).encode(),
            "topic": topic.encode(),
            "log_time_ns": str(log_time_ns).encode(),
            "frame_id": frame_id.encode(),
            "source_point_count": str(source_point_count).encode(),
            "point_count": str(int(valid.sum())).encode(),
            "bounds": json.dumps(bounds, separators=(",", ":")).encode(),
            "coordinate_unit": b"meter",
        },
    )
    table = pa.table(columns, schema=schema)
    buffer = io.BytesIO()
    with ipc.new_stream(buffer, schema) as writer:
        writer.write_table(table)
    return PointCloudPayload(data=buffer.getvalue(), log_time_ns=log_time_ns)
