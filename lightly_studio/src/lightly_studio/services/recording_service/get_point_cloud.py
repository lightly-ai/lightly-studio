"""Reads and serializes one MCAP PointCloud2 message as Arrow IPC."""

from __future__ import annotations

import io
import json
from dataclasses import dataclass
from typing import Any, Literal
from uuid import UUID

import numpy as np
import pyarrow as pa
from numpy.typing import NDArray
from pyarrow import ipc
from sqlmodel import Session

from lightly_studio.core.mcap.errors import ChannelNotFoundError, McapAccessError
from lightly_studio.core.mcap.topic_kind import TopicKind
from lightly_studio.resolvers import recording_resolver
from lightly_studio.services.recording_service.reader_cache import get_cached_reader

_FLOAT32_DATATYPE = 7
_POINT_FIELD_DTYPES: dict[int, str] = {
    1: "i1",
    2: "u1",
    3: "<i2",
    4: "<u2",
    5: "<i4",
    6: "<u4",
    _FLOAT32_DATATYPE: "<f4",
    8: "<f8",
}
# The sRGB component below which the transfer function is linear.
_SRGB_LINEAR_THRESHOLD = 0.04045


@dataclass(frozen=True)
class PointCloudPayload:
    """Serialized point data ready to serve over HTTP."""

    data: bytes
    log_time_ns: int


@dataclass(frozen=True)
class _PointCloudLayout:
    """Byte layout shared by every field of one PointCloud2 message."""

    width: int
    height: int
    point_step: int
    row_step: int
    endian: Literal[">", "<"]


def get_point_cloud(
    session: Session,
    dataset_id: UUID,
    recording_id: UUID,
    channel_id: int,
    timestamp_ns: int,
) -> PointCloudPayload | None:
    """Return one decoded point-cloud message as an Arrow IPC stream."""
    recording = recording_resolver.get_by_id(session=session, recording_id=recording_id)
    if recording is None or recording.dataset_id != dataset_id:
        return None
    reader = get_cached_reader(recording.uri)
    topic = next((topic for topic in reader.get_topics() if topic.channel_id == channel_id), None)
    if topic is None:
        raise ChannelNotFoundError(f"Channel {channel_id} was not found.")
    if topic.kind is not TopicKind.POINT_CLOUD:
        raise McapAccessError(f"Channel {channel_id} does not carry a point cloud.")
    message = reader.get_decoded_message_at(channel_id=channel_id, timestamp_ns=timestamp_ns)
    if message is None:
        return None
    return _serialize_point_cloud(
        message=message.decoded_message,
        channel_id=channel_id,
        topic=topic.name,
        log_time_ns=message.log_time_ns,
    )


def _serialize_point_cloud(
    message: object, channel_id: int, topic: str, log_time_ns: int
) -> PointCloudPayload:
    """Decode PointCloud2 fields and serialize point rows with frame metadata."""
    width = int(_value(message, "width"))
    height = int(_value(message, "height"))
    point_step = int(_value(message, "point_step"))
    row_step = int(_value(message, "row_step"))
    data = bytes(_value(message, "data"))
    fields = {str(_value(field, "name")): field for field in _value(message, "fields")}
    required = {name for name in ("x", "y", "z") if name not in fields}
    if required:
        missing = ", ".join(sorted(required))
        raise McapAccessError(f"Point cloud is missing required fields: {missing}.")
    if point_step <= 0 or len(data) < row_step * height:
        raise McapAccessError("Point cloud has invalid row or point data dimensions.")
    endian: Literal[">", "<"] = ">" if bool(_value(message, "is_bigendian")) else "<"
    layout = _PointCloudLayout(
        width=width, height=height, point_step=point_step, row_step=row_step, endian=endian
    )
    points: dict[str, NDArray[Any]] = {
        name: _read_field(data, fields[name], layout) for name in ("x", "y", "z")
    }
    source_point_count = width * height
    xyz = np.column_stack((points["x"], points["y"], points["z"])).astype(np.float32)
    valid = np.isfinite(xyz).all(axis=1)
    columns: dict[str, pa.Array] = {
        name: pa.array(xyz[valid, index], type=pa.float32())
        for index, name in enumerate(("x", "y", "z"))
    }
    if "intensity" in fields:
        intensity = _read_field(data, fields["intensity"], layout)
        columns["intensity"] = pa.array(_normalize(intensity[valid]), type=pa.float32())
    colors = _read_colors(data, fields, layout)
    if colors is not None:
        for index, name in enumerate(("r", "g", "b")):
            # PointCloud2 RGB fields are sRGB; the renderer contract uses linear RGB.
            srgb = colors[valid, index].astype(np.float32) / 255.0
            columns[name] = pa.array(
                np.where(
                    srgb <= _SRGB_LINEAR_THRESHOLD,
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
    frame_id = str(_value(_value(message, "header"), "frame_id"))
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


def _read_field(data: bytes, field: object, layout: _PointCloudLayout) -> NDArray[Any]:
    """Read a scalar PointField as a flat numeric array."""
    datatype = int(_value(field, "datatype"))
    if datatype not in _POINT_FIELD_DTYPES or int(_value(field, "count")) != 1:
        raise McapAccessError(f"Unsupported PointCloud2 field '{_value(field, 'name')}'.")
    dtype = np.dtype(_POINT_FIELD_DTYPES[datatype])
    if dtype.itemsize > 1:
        dtype = dtype.newbyteorder(layout.endian)
    values: NDArray[Any] = np.ndarray(
        shape=(layout.height, layout.width),
        dtype=dtype,
        buffer=data,
        offset=int(_value(field, "offset")),
        strides=(layout.row_step, layout.point_step),
    )
    return values.reshape(-1)


def _read_colors(
    data: bytes, fields: dict[str, object], layout: _PointCloudLayout
) -> NDArray[Any] | None:
    """Read separate RGB fields or the common packed rgb/rgba PointCloud2 field."""
    if all(name in fields for name in ("r", "g", "b")):
        return np.column_stack(
            [_read_field(data, fields[name], layout) for name in ("r", "g", "b")]
        )
    packed_name = "rgb" if "rgb" in fields else "rgba" if "rgba" in fields else None
    if packed_name is None:
        return None
    packed_field = fields[packed_name]
    datatype = int(_value(packed_field, "datatype"))
    if datatype == _FLOAT32_DATATYPE:
        packed: NDArray[Any] = np.ndarray(
            shape=(layout.height, layout.width),
            dtype=np.dtype(f"{layout.endian}u4"),
            buffer=data,
            offset=int(_value(packed_field, "offset")),
            strides=(layout.row_step, layout.point_step),
        ).reshape(-1)
    else:
        packed = _read_field(data, packed_field, layout)
    packed = packed.astype(np.uint32, copy=False)
    return np.column_stack(((packed >> 16) & 255, (packed >> 8) & 255, packed & 255))


def _normalize(values: NDArray[Any]) -> NDArray[Any]:
    """Scale finite sensor intensity values into the renderer's [0, 1] range."""
    values = values.astype(np.float32)
    finite = np.isfinite(values)
    if not finite.any():
        return np.zeros_like(values)
    minimum = float(values[finite].min())
    maximum = float(values[finite].max())
    if maximum <= minimum:
        return np.zeros_like(values)
    normalized = np.clip((values - minimum) / (maximum - minimum), 0.0, 1.0)
    normalized[~finite] = 0.0
    return normalized


def _value(value: object, name: str) -> Any:
    """Read a field from a decoded ROS message or mapping."""
    if isinstance(value, dict):
        return value[name]
    return getattr(value, name)
