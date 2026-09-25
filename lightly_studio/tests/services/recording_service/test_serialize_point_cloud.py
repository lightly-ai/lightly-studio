"""Tests for PointCloud2 serialization."""

import io
import json
import struct

import pyarrow as pa
import pytest
from pyarrow import ipc

from lightly_studio.core.mcap.errors import McapAccessError
from lightly_studio.services.recording_service import serialize_point_cloud
from lightly_studio.services.recording_service.point_cloud_types import PointCloudPayload

_UINT8_DATATYPE = 2
_FLOAT32_DATATYPE = 7


def _field(name: str, datatype: int, offset: int) -> dict[str, object]:
    return {"name": name, "datatype": datatype, "count": 1, "offset": offset}


def _xyz_fields() -> list[dict[str, object]]:
    return [
        _field(name=name, datatype=_FLOAT32_DATATYPE, offset=index * 4)
        for index, name in enumerate(("x", "y", "z"))
    ]


def _read_table(payload: PointCloudPayload) -> pa.Table:
    with ipc.open_stream(io.BytesIO(payload.data)) as stream:
        return stream.read_all()


def test_serialize_point_cloud() -> None:
    message = {
        "width": 1,
        "height": 1,
        "point_step": 12,
        "row_step": 12,
        "data": struct.pack("<fff", 1.0, 2.0, 3.0),
        "fields": _xyz_fields(),
        "is_bigendian": False,
        "header": {"frame_id": "map"},
    }

    payload = serialize_point_cloud.serialize_point_cloud(
        message=message, channel_id=4, topic="/points", log_time_ns=123
    )

    table = _read_table(payload=payload)
    assert table.column_names == ["x", "y", "z"]
    assert table.column("x").to_pylist() == [1.0]
    assert table.schema.metadata[b"frame_id"] == b"map"
    assert table.schema.metadata[b"channel_id"] == b"4"
    assert table.schema.metadata[b"topic"] == b"/points"
    assert table.schema.metadata[b"log_time_ns"] == b"123"
    assert table.schema.metadata[b"source_point_count"] == b"1"
    assert table.schema.metadata[b"point_count"] == b"1"
    assert table.schema.metadata[b"coordinate_unit"] == b"meter"
    assert json.loads(table.schema.metadata[b"bounds"]) == {
        "min": [1.0, 2.0, 3.0],
        "max": [1.0, 2.0, 3.0],
    }
    assert payload.log_time_ns == 123
    assert pa.types.is_float32(table.schema.field("x").type)


def test_serialize_point_cloud__propagates_invalid_message() -> None:
    message = {
        "width": 1,
        "height": 1,
        "point_step": 8,
        "row_step": 8,
        "data": struct.pack("<ff", 1.0, 2.0),
        "fields": [
            _field(name="x", datatype=_FLOAT32_DATATYPE, offset=0),
            _field(name="y", datatype=_FLOAT32_DATATYPE, offset=4),
        ],
        "is_bigendian": False,
        "header": {"frame_id": "map"},
    }

    with pytest.raises(McapAccessError, match="missing required fields: z"):
        serialize_point_cloud.serialize_point_cloud(
            message=message, channel_id=0, topic="/points", log_time_ns=0
        )


def test_serialize_point_cloud__drops_non_finite_points() -> None:
    message = {
        "width": 2,
        "height": 1,
        "point_step": 12,
        "row_step": 24,
        "data": struct.pack("<ffffff", 1.0, 2.0, 3.0, float("nan"), 5.0, 6.0),
        "fields": _xyz_fields(),
        "is_bigendian": False,
        "header": {"frame_id": "map"},
    }

    payload = serialize_point_cloud.serialize_point_cloud(
        message=message, channel_id=0, topic="/points", log_time_ns=0
    )

    table = _read_table(payload=payload)
    assert table.column("x").to_pylist() == [1.0]
    assert table.schema.metadata[b"source_point_count"] == b"2"
    assert table.schema.metadata[b"point_count"] == b"1"


def test_serialize_point_cloud__serializes_intensity_and_colors() -> None:
    message = {
        "width": 1,
        "height": 1,
        "point_step": 19,
        "row_step": 19,
        "data": struct.pack("<ffffBBB", 1.0, 2.0, 3.0, 10.0, 0, 255, 10),
        "fields": [
            *_xyz_fields(),
            _field(name="intensity", datatype=_FLOAT32_DATATYPE, offset=12),
            _field(name="r", datatype=_UINT8_DATATYPE, offset=16),
            _field(name="g", datatype=_UINT8_DATATYPE, offset=17),
            _field(name="b", datatype=_UINT8_DATATYPE, offset=18),
        ],
        "is_bigendian": False,
        "header": {"frame_id": "map"},
    }

    payload = serialize_point_cloud.serialize_point_cloud(
        message=message, channel_id=0, topic="/points", log_time_ns=0
    )

    table = _read_table(payload=payload)
    assert table.column_names == ["x", "y", "z", "intensity", "r", "g", "b"]
    assert pa.types.is_float32(table.schema.field("intensity").type)


def test_serialize_point_cloud__reads_big_endian_data() -> None:
    message = {
        "width": 1,
        "height": 1,
        "point_step": 12,
        "row_step": 12,
        "data": struct.pack(">fff", 1.0, 2.0, 3.0),
        "fields": _xyz_fields(),
        "is_bigendian": True,
        "header": {"frame_id": "map"},
    }

    payload = serialize_point_cloud.serialize_point_cloud(
        message=message, channel_id=0, topic="/points", log_time_ns=0
    )

    table = _read_table(payload=payload)
    assert table.column("x").to_pylist() == [1.0]
    assert table.column("z").to_pylist() == [3.0]
