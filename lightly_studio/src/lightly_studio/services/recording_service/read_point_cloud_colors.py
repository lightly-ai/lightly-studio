"""Read RGB values from PointCloud2 fields."""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

from lightly_studio.services.recording_service import point_cloud_value, read_point_cloud_field
from lightly_studio.services.recording_service.point_cloud_types import (
    FLOAT32_DATATYPE,
    PointCloudLayout,
)


def read_point_cloud_colors(
    data: bytes, fields: dict[str, object], layout: PointCloudLayout
) -> NDArray[Any] | None:
    """Read separate RGB fields or the common packed rgb/rgba PointCloud2 field."""
    if all(name in fields for name in ("r", "g", "b")):
        return np.column_stack(
            [
                read_point_cloud_field.read_point_cloud_field(data, fields[name], layout)
                for name in ("r", "g", "b")
            ]
        )
    packed_name = "rgb" if "rgb" in fields else "rgba" if "rgba" in fields else None
    if packed_name is None:
        return None
    packed_field = fields[packed_name]
    datatype = int(point_cloud_value.get_value(packed_field, "datatype"))
    if datatype == FLOAT32_DATATYPE:
        packed: NDArray[Any] = np.ndarray(
            shape=(layout.height, layout.width),
            dtype=np.dtype(f"{layout.endian}u4"),
            buffer=data,
            offset=int(point_cloud_value.get_value(packed_field, "offset")),
            strides=(layout.row_step, layout.point_step),
        ).reshape(-1)
    else:
        packed = read_point_cloud_field.read_point_cloud_field(data, packed_field, layout)
    packed = packed.astype(np.uint32, copy=False)
    return np.column_stack(((packed >> 16) & 255, (packed >> 8) & 255, packed & 255))
