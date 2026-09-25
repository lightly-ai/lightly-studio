"""Tests for reading scalar PointCloud2 fields."""

from types import SimpleNamespace

import numpy as np
import pytest

from lightly_studio.core.mcap.errors import McapAccessError
from lightly_studio.services.recording_service import read_point_cloud_field
from lightly_studio.services.recording_service.point_cloud_types import PointCloudLayout


def test_read_point_cloud_field() -> None:
    field = SimpleNamespace(name="x", datatype=7, count=1, offset=0)
    layout = PointCloudLayout(width=2, height=1, point_step=4, row_step=8, endian="<")
    data = np.array([1.5, 2.5], dtype="<f4").tobytes()

    result = read_point_cloud_field.read_point_cloud_field(data=data, field=field, layout=layout)

    np.testing.assert_array_equal(result, np.array([1.5, 2.5], dtype="<f4"))


def test_read_point_cloud_field__single_byte_datatype() -> None:
    field = SimpleNamespace(name="ring", datatype=1, count=1, offset=0)
    layout = PointCloudLayout(width=2, height=1, point_step=1, row_step=2, endian=">")
    data = np.array([3, -4], dtype="i1").tobytes()

    result = read_point_cloud_field.read_point_cloud_field(data=data, field=field, layout=layout)

    np.testing.assert_array_equal(result, np.array([3, -4], dtype="i1"))


def test_read_point_cloud_field__unsupported_datatype() -> None:
    field = SimpleNamespace(name="x", datatype=0, count=1, offset=0)
    layout = PointCloudLayout(width=1, height=1, point_step=4, row_step=4, endian="<")

    with pytest.raises(McapAccessError, match="Unsupported PointCloud2 field 'x'"):
        read_point_cloud_field.read_point_cloud_field(data=b"\x00" * 4, field=field, layout=layout)


def test_read_point_cloud_field__unsupported_count() -> None:
    field = SimpleNamespace(name="x", datatype=7, count=2, offset=0)
    layout = PointCloudLayout(width=1, height=1, point_step=4, row_step=4, endian="<")

    with pytest.raises(McapAccessError, match="Unsupported PointCloud2 field 'x'"):
        read_point_cloud_field.read_point_cloud_field(data=b"\x00" * 4, field=field, layout=layout)
