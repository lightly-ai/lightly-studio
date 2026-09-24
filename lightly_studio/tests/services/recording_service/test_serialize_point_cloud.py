"""Tests for PointCloud2 serialization."""

import io
import struct

import pyarrow as pa
from pyarrow import ipc

from lightly_studio.services.recording_service import serialize_point_cloud


def test_serialize_point_cloud() -> None:
    message = {
        "width": 1,
        "height": 1,
        "point_step": 12,
        "row_step": 12,
        "data": struct.pack("<fff", 1.0, 2.0, 3.0),
        "fields": [
            {"name": name, "datatype": 7, "count": 1, "offset": index * 4}
            for index, name in enumerate(("x", "y", "z"))
        ],
        "is_bigendian": False,
        "header": {"frame_id": "map"},
    }

    payload = serialize_point_cloud.serialize_point_cloud(
        message=message, channel_id=4, topic="/points", log_time_ns=123
    )

    with ipc.open_stream(io.BytesIO(payload.data)) as stream:
        table = stream.read_all()
    assert table.column_names == ["x", "y", "z"]
    assert table.column("x").to_pylist() == [1.0]
    assert table.schema.metadata[b"frame_id"] == b"map"
    assert table.schema.metadata[b"channel_id"] == b"4"
    assert payload.log_time_ns == 123
    assert pa.types.is_float32(table.schema.field("x").type)
