"""Tests for building the Arrow columns of a serialized point cloud."""

import struct
from types import SimpleNamespace

import numpy as np
import pytest

from lightly_studio.services.recording_service import build_point_cloud_columns
from lightly_studio.services.recording_service.point_cloud_types import PointCloudLayout

_UINT8_DATATYPE = 2
_FLOAT32_DATATYPE = 7


def _field(name: str, datatype: int, offset: int) -> SimpleNamespace:
    return SimpleNamespace(name=name, datatype=datatype, count=1, offset=offset)


def _xyz_fields() -> dict[str, object]:
    return {
        name: _field(name=name, datatype=_FLOAT32_DATATYPE, offset=index * 4)
        for index, name in enumerate(("x", "y", "z"))
    }


def test_build_point_cloud_columns() -> None:
    layout = PointCloudLayout(width=1, height=1, point_step=12, row_step=12, endian="<")
    data = struct.pack("<fff", 1.0, 2.0, 3.0)
    xyz = np.array([[1.0, 2.0, 3.0]], dtype=np.float32)
    valid = np.array([True])

    columns = build_point_cloud_columns.build_point_cloud_columns(
        data=data, fields=_xyz_fields(), layout=layout, xyz=xyz, valid=valid
    )

    assert list(columns) == ["x", "y", "z"]
    assert columns["x"].to_pylist() == [1.0]
    assert columns["z"].to_pylist() == [3.0]


def test_build_point_cloud_columns__drops_invalid_points() -> None:
    layout = PointCloudLayout(width=2, height=1, point_step=12, row_step=24, endian="<")
    data = struct.pack("<ffffff", 1.0, 2.0, 3.0, 4.0, 5.0, 6.0)
    xyz = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]], dtype=np.float32)
    valid = np.array([True, False])

    columns = build_point_cloud_columns.build_point_cloud_columns(
        data=data, fields=_xyz_fields(), layout=layout, xyz=xyz, valid=valid
    )

    assert columns["x"].to_pylist() == [1.0]


def test_build_point_cloud_columns__normalizes_intensity() -> None:
    layout = PointCloudLayout(width=2, height=1, point_step=16, row_step=32, endian="<")
    data = struct.pack("<ffffffff", 1.0, 2.0, 3.0, 10.0, 4.0, 5.0, 6.0, 20.0)
    fields = {**_xyz_fields(), "intensity": _field("intensity", _FLOAT32_DATATYPE, 12)}
    xyz = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]], dtype=np.float32)
    valid = np.array([True, True])

    columns = build_point_cloud_columns.build_point_cloud_columns(
        data=data, fields=fields, layout=layout, xyz=xyz, valid=valid
    )

    # The two distinct intensities scale to the renderer's [0, 1] range.
    assert columns["intensity"].to_pylist() == pytest.approx([0.0, 1.0])


def test_build_point_cloud_columns__converts_srgb_colors_to_linear() -> None:
    layout = PointCloudLayout(width=1, height=1, point_step=15, row_step=15, endian="<")
    data = struct.pack("<fffBBB", 1.0, 2.0, 3.0, 0, 255, 10)
    fields = {
        **_xyz_fields(),
        "r": _field("r", _UINT8_DATATYPE, 12),
        "g": _field("g", _UINT8_DATATYPE, 13),
        "b": _field("b", _UINT8_DATATYPE, 14),
    }
    xyz = np.array([[1.0, 2.0, 3.0]], dtype=np.float32)
    valid = np.array([True])

    columns = build_point_cloud_columns.build_point_cloud_columns(
        data=data, fields=fields, layout=layout, xyz=xyz, valid=valid
    )

    assert list(columns) == ["x", "y", "z", "r", "g", "b"]
    assert columns["r"].to_pylist() == pytest.approx([0.0])
    assert columns["g"].to_pylist() == pytest.approx([1.0])
    assert columns["b"].to_pylist() == pytest.approx([(10 / 255) / 12.92])
