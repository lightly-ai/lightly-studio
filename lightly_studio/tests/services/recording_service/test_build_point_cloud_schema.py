"""Tests for building the Arrow schema of a serialized point cloud."""

import json

import numpy as np
import pyarrow as pa

from lightly_studio.services.recording_service import build_point_cloud_schema
from lightly_studio.services.recording_service.point_cloud_types import PointCloudFrameMetadata


def _metadata() -> PointCloudFrameMetadata:
    return PointCloudFrameMetadata(
        channel_id=4,
        topic="/points",
        log_time_ns=123,
        frame_id="map",
        source_point_count=2,
    )


def test_build_point_cloud_schema() -> None:
    columns = {name: pa.array([1.0], type=pa.float32()) for name in ("x", "y", "z")}
    xyz_valid = np.array([[1.0, 2.0, 3.0]], dtype=np.float32)

    schema = build_point_cloud_schema.build_point_cloud_schema(
        columns=columns, metadata=_metadata(), xyz_valid=xyz_valid
    )

    assert schema.names == ["x", "y", "z"]
    assert pa.types.is_float32(schema.field("x").type)
    assert schema.metadata[b"channel_id"] == b"4"
    assert schema.metadata[b"topic"] == b"/points"
    assert schema.metadata[b"log_time_ns"] == b"123"
    assert schema.metadata[b"frame_id"] == b"map"
    assert schema.metadata[b"source_point_count"] == b"2"
    assert schema.metadata[b"point_count"] == b"1"
    assert schema.metadata[b"coordinate_unit"] == b"meter"
    assert json.loads(schema.metadata[b"bounds"]) == {
        "min": [1.0, 2.0, 3.0],
        "max": [1.0, 2.0, 3.0],
    }


def test_build_point_cloud_schema__empty_bounds_when_no_points() -> None:
    columns = {name: pa.array([], type=pa.float32()) for name in ("x", "y", "z")}
    xyz_valid = np.empty((0, 3), dtype=np.float32)

    schema = build_point_cloud_schema.build_point_cloud_schema(
        columns=columns, metadata=_metadata(), xyz_valid=xyz_valid
    )

    assert schema.metadata[b"point_count"] == b"0"
    assert json.loads(schema.metadata[b"bounds"]) is None
