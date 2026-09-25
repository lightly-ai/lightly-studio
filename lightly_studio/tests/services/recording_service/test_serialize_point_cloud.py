"""Tests for PointCloud2 serialization."""

import io
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


def _message(
    data: bytes,
    fields: list[dict[str, object]],
    width: int = 1,
    point_step: int = 12,
    is_bigendian: bool = False,
) -> dict[str, object]:
    return {
        "width": width,
        "height": 1,
        "point_step": point_step,
        "row_step": point_step * width,
        "data": data,
        "fields": fields,
        "is_bigendian": is_bigendian,
        "header": {"frame_id": "map"},
    }


def _serialize(
    message: dict[str, object],
    channel_id: int = 0,
    topic: str = "/points",
    log_time_ns: int = 0,
) -> PointCloudPayload:
    return serialize_point_cloud.serialize_point_cloud(
        message=message, channel_id=channel_id, topic=topic, log_time_ns=log_time_ns
    )


def _read_table(payload: PointCloudPayload) -> pa.Table:
    with ipc.open_stream(io.BytesIO(payload.data)) as stream:
        return stream.read_all()


@pytest.mark.parametrize("is_bigendian", [False, True])
def test_serialize_point_cloud(is_bigendian: bool) -> None:
    byte_order = ">" if is_bigendian else "<"
    message = _message(
        data=struct.pack(f"{byte_order}fff", 1.0, 2.0, 3.0),
        fields=_xyz_fields(),
        is_bigendian=is_bigendian,
    )

    payload = _serialize(message=message, channel_id=4, topic="/points", log_time_ns=123)

    table = _read_table(payload=payload)
    assert table.column_names == ["x", "y", "z"]
    assert table.column("x").to_pylist() == [1.0]
    assert table.column("z").to_pylist() == [3.0]
    assert pa.types.is_float32(table.schema.field("x").type)
    assert payload.log_time_ns == 123
    metadata = table.schema.metadata
    assert metadata[b"channel_id"] == b"4"
    assert metadata[b"topic"] == b"/points"
    assert metadata[b"log_time_ns"] == b"123"
    assert metadata[b"frame_id"] == b"map"


def test_serialize_point_cloud__propagates_invalid_message() -> None:
    message = _message(
        data=struct.pack("<ff", 1.0, 2.0),
        fields=[
            _field(name="x", datatype=_FLOAT32_DATATYPE, offset=0),
            _field(name="y", datatype=_FLOAT32_DATATYPE, offset=4),
        ],
        point_step=8,
    )

    with pytest.raises(McapAccessError, match="missing required fields: z"):
        _serialize(message=message)


def test_serialize_point_cloud__drops_non_finite_points() -> None:
    message = _message(
        data=struct.pack("<ffffff", 1.0, 2.0, 3.0, float("nan"), 5.0, 6.0),
        fields=_xyz_fields(),
        width=2,
    )

    payload = _serialize(message=message)

    table = _read_table(payload=payload)
    assert table.column("x").to_pylist() == [1.0]
    assert table.schema.metadata[b"source_point_count"] == b"2"
    assert table.schema.metadata[b"point_count"] == b"1"


def test_serialize_point_cloud__serializes_intensity_and_colors() -> None:
    message = _message(
        data=struct.pack("<ffffBBB", 1.0, 2.0, 3.0, 10.0, 0, 255, 10),
        fields=[
            *_xyz_fields(),
            _field(name="intensity", datatype=_FLOAT32_DATATYPE, offset=12),
            _field(name="r", datatype=_UINT8_DATATYPE, offset=16),
            _field(name="g", datatype=_UINT8_DATATYPE, offset=17),
            _field(name="b", datatype=_UINT8_DATATYPE, offset=18),
        ],
        point_step=19,
    )

    payload = _serialize(message=message)

    table = _read_table(payload=payload)
    assert table.column_names == ["x", "y", "z", "intensity", "r", "g", "b"]
    assert pa.types.is_float32(table.schema.field("intensity").type)
