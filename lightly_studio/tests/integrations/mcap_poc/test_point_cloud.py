"""Tests for ROS 2 PointCloud2 decoding."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from lightly_studio.integrations.mcap_poc import point_cloud


def test_decode_point_cloud2_filters_invalid_points_and_uses_reflectivity() -> None:
    dtype = np.dtype(
        {
            "names": ["x", "y", "z", "reflectivity"],
            "formats": ["<f4", "<f4", "<f4", "u1"],
            "offsets": [0, 4, 8, 12],
            "itemsize": 16,
        }
    )
    values = np.zeros(3, dtype=dtype)
    values["x"] = [1, np.nan, 7]
    values["y"] = [2, 5, 8]
    values["z"] = [3, 6, 9]
    values["reflectivity"] = [4, 10, 11]
    message = _message(data=values.tobytes(), width=3)

    result = point_cloud.decode_point_cloud2(message=message)

    np.testing.assert_array_equal(
        result,
        np.asarray([[1, 2, 3, 4], [7, 8, 9, 11]], dtype=np.float32),
    )


def test_decode_point_cloud2_honors_row_padding() -> None:
    data = bytearray(60)
    values = [
        (1.0, 2.0, 3.0),
        (4.0, 5.0, 6.0),
        (7.0, 8.0, 9.0),
        (10.0, 11.0, 12.0),
    ]
    for offset, value in zip((0, 16, 28, 44), values):
        data[offset : offset + 12] = np.asarray(value, dtype="<f4").tobytes()
    message = _message(data=bytes(data), width=2, height=2, row_step=28)

    result = point_cloud.decode_point_cloud2(message=message)

    np.testing.assert_array_equal(result[:, :3], np.asarray(values, dtype=np.float32))


def test_decode_point_cloud2_rejects_missing_coordinate() -> None:
    message = _message(data=bytes(16), width=1)
    message.fields = message.fields[:2]

    with pytest.raises(ValueError, match="missing required fields: z"):
        point_cloud.decode_point_cloud2(message=message)


def _message(
    data: bytes,
    width: int,
    height: int = 1,
    row_step: int | None = None,
) -> SimpleNamespace:
    names = ("x", "y", "z", "reflectivity")
    fields = [
        SimpleNamespace(name=name, offset=index * 4, datatype=7, count=1)
        for index, name in enumerate(names[:3])
    ]
    fields.append(SimpleNamespace(name="reflectivity", offset=12, datatype=2, count=1))
    return SimpleNamespace(
        fields=fields,
        data=data,
        width=width,
        height=height,
        point_step=16,
        row_step=row_step or width * 16,
        is_bigendian=False,
    )
