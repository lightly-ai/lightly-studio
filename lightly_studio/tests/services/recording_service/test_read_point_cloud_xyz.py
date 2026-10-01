"""Tests for stacking the x, y, and z coordinate fields."""

import struct
from types import SimpleNamespace

import numpy as np

from lightly_studio.services.recording_service import read_point_cloud_xyz
from lightly_studio.services.recording_service.point_cloud_types import PointCloudLayout


def _xyz_fields() -> dict[str, object]:
    return {
        name: SimpleNamespace(name=name, datatype=7, count=1, offset=index * 4)
        for index, name in enumerate(("x", "y", "z"))
    }


def test_read_point_cloud_xyz() -> None:
    layout = PointCloudLayout(width=2, height=1, point_step=12, row_step=24, endian="<")
    data = struct.pack("<ffffff", 1.0, 2.0, 3.0, 4.0, 5.0, 6.0)

    result = read_point_cloud_xyz.read_point_cloud_xyz(
        data=data, fields=_xyz_fields(), layout=layout
    )

    assert result.dtype == np.float32
    np.testing.assert_array_equal(
        result, np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]], dtype=np.float32)
    )
