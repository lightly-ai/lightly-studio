"""Tests for reading the byte layout of a PointCloud2 message."""

import struct

import pytest

from lightly_studio.core.mcap.errors import McapAccessError
from lightly_studio.services.recording_service import read_point_cloud_layout


def _field(name: str, offset: int) -> dict[str, object]:
    return {"name": name, "datatype": 7, "count": 1, "offset": offset}


def _xyz_fields() -> list[dict[str, object]]:
    return [_field(name=name, offset=index * 4) for index, name in enumerate(("x", "y", "z"))]


def test_read_point_cloud_layout() -> None:
    message = {
        "width": 1,
        "height": 1,
        "point_step": 12,
        "row_step": 12,
        "data": struct.pack("<fff", 1.0, 2.0, 3.0),
        "fields": _xyz_fields(),
        "is_bigendian": False,
    }

    layout, data, fields = read_point_cloud_layout.read_point_cloud_layout(message=message)

    assert layout.width == 1
    assert layout.height == 1
    assert layout.point_step == 12
    assert layout.row_step == 12
    assert layout.endian == "<"
    assert data == struct.pack("<fff", 1.0, 2.0, 3.0)
    assert set(fields) == {"x", "y", "z"}


def test_read_point_cloud_layout__big_endian() -> None:
    message = {
        "width": 1,
        "height": 1,
        "point_step": 12,
        "row_step": 12,
        "data": struct.pack(">fff", 1.0, 2.0, 3.0),
        "fields": _xyz_fields(),
        "is_bigendian": True,
    }

    layout, _, _ = read_point_cloud_layout.read_point_cloud_layout(message=message)

    assert layout.endian == ">"


def test_read_point_cloud_layout__missing_required_field() -> None:
    message = {
        "width": 1,
        "height": 1,
        "point_step": 8,
        "row_step": 8,
        "data": struct.pack("<ff", 1.0, 2.0),
        "fields": [_field(name="x", offset=0), _field(name="y", offset=4)],
        "is_bigendian": False,
    }

    with pytest.raises(McapAccessError, match="missing required fields: z"):
        read_point_cloud_layout.read_point_cloud_layout(message=message)


def test_read_point_cloud_layout__negative_dimension() -> None:
    message = {
        "width": -1,
        "height": 1,
        "point_step": 12,
        "row_step": 12,
        "data": struct.pack("<fff", 1.0, 2.0, 3.0),
        "fields": _xyz_fields(),
        "is_bigendian": False,
    }

    with pytest.raises(McapAccessError, match="invalid row or point data dimensions"):
        read_point_cloud_layout.read_point_cloud_layout(message=message)


def test_read_point_cloud_layout__row_step_too_small_for_points() -> None:
    # Two points per row but a row only wide enough for one.
    message = {
        "width": 2,
        "height": 1,
        "point_step": 12,
        "row_step": 12,
        "data": struct.pack("<fff", 1.0, 2.0, 3.0),
        "fields": _xyz_fields(),
        "is_bigendian": False,
    }

    with pytest.raises(McapAccessError, match="invalid row or point data dimensions"):
        read_point_cloud_layout.read_point_cloud_layout(message=message)


def test_read_point_cloud_layout__data_shorter_than_rows() -> None:
    message = {
        "width": 1,
        "height": 2,
        "point_step": 12,
        "row_step": 12,
        "data": struct.pack("<fff", 1.0, 2.0, 3.0),
        "fields": _xyz_fields(),
        "is_bigendian": False,
    }

    with pytest.raises(McapAccessError, match="invalid row or point data dimensions"):
        read_point_cloud_layout.read_point_cloud_layout(message=message)
