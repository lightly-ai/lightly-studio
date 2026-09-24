"""Tests for reading PointCloud2 color fields."""

from types import SimpleNamespace

import numpy as np

from lightly_studio.services.recording_service import read_point_cloud_colors
from lightly_studio.services.recording_service.point_cloud_types import PointCloudLayout


def test_read_point_cloud_colors__packed_rgb() -> None:
    field = SimpleNamespace(name="rgb", datatype=7, count=1, offset=0)
    layout = PointCloudLayout(width=1, height=1, point_step=4, row_step=4, endian="<")
    data = np.array([0x00112233], dtype="<u4").tobytes()

    result = read_point_cloud_colors.read_point_cloud_colors(
        data, {"rgb": field}, layout
    )

    np.testing.assert_array_equal(result, np.array([[0x11, 0x22, 0x33]], dtype=np.uint32))


def test_read_point_cloud_colors__separate_channels() -> None:
    fields = {
        name: SimpleNamespace(name=name, datatype=2, count=1, offset=index)
        for index, name in enumerate(("r", "g", "b"))
    }
    layout = PointCloudLayout(width=1, height=1, point_step=3, row_step=3, endian="<")

    result = read_point_cloud_colors.read_point_cloud_colors(b"\x11\x22\x33", fields, layout)

    np.testing.assert_array_equal(result, np.array([[0x11, 0x22, 0x33]], dtype=np.uint8))


def test_read_point_cloud_colors__missing_fields() -> None:
    layout = PointCloudLayout(width=1, height=1, point_step=1, row_step=1, endian="<")

    assert read_point_cloud_colors.read_point_cloud_colors(b"\x00", {}, layout) is None
