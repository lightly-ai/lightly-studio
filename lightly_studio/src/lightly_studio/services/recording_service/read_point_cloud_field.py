"""Read one scalar field from a PointCloud2 message."""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

from lightly_studio.core.mcap.errors import McapAccessError
from lightly_studio.services.recording_service import point_cloud_value
from lightly_studio.services.recording_service.point_cloud_types import (
    POINT_FIELD_DTYPES,
    PointCloudLayout,
)


def read_point_cloud_field(data: bytes, field: object, layout: PointCloudLayout) -> NDArray[Any]:
    """Read a scalar PointField as a flat numeric array."""
    datatype = int(point_cloud_value.get_value(value=field, name="datatype"))
    if (
        datatype not in POINT_FIELD_DTYPES
        or int(point_cloud_value.get_value(value=field, name="count")) != 1
    ):
        name = point_cloud_value.get_value(value=field, name="name")
        raise McapAccessError(f"Unsupported PointCloud2 field '{name}'.")
    dtype = np.dtype(POINT_FIELD_DTYPES[datatype])
    if dtype.itemsize > 1:
        dtype = dtype.newbyteorder(layout.endian)
    values: NDArray[Any] = np.ndarray(
        shape=(layout.height, layout.width),
        dtype=dtype,
        buffer=data,
        offset=int(point_cloud_value.get_value(field, "offset")),
        strides=(layout.row_step, layout.point_step),
    )
    return values.reshape(-1)
