"""Build the Arrow columns of a serialized point cloud."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pyarrow as pa
from numpy.typing import NDArray

from lightly_studio.services.recording_service import (
    normalize_point_cloud_intensity,
    read_point_cloud_colors,
    read_point_cloud_field,
    srgb_to_linear,
)
from lightly_studio.services.recording_service.point_cloud_types import PointCloudLayout


def build_point_cloud_columns(
    data: bytes,
    fields: Mapping[str, object],
    layout: PointCloudLayout,
    xyz: NDArray[np.float32],
    valid: NDArray[np.bool_],
) -> dict[str, pa.Array]:
    """Build the Arrow columns for coordinates, optional intensity, and color.

    N is the number of points in the message.

    Args:
        data: The raw PointCloud2 data buffer.
        fields: A map of field name to the PointField describing it.
        layout: The byte layout shared by every field of the message.
        xyz: The stacked coordinates of shape (N, 3).
        valid: A mask of shape (N,) selecting the finite points to keep.

    Returns:
        A map of column name to its Arrow float32 array.
    """
    columns: dict[str, pa.Array] = {
        name: pa.array(xyz[valid, index], type=pa.float32())
        for index, name in enumerate(("x", "y", "z"))
    }
    if "intensity" in fields:
        intensity = read_point_cloud_field.read_point_cloud_field(
            data=data, field=fields["intensity"], layout=layout
        )
        columns["intensity"] = pa.array(
            normalize_point_cloud_intensity.normalize_point_cloud_intensity(
                values=intensity[valid]
            ),
            type=pa.float32(),
        )
    colors = read_point_cloud_colors.read_point_cloud_colors(
        data=data, fields=fields, layout=layout
    )
    if colors is not None:
        for index, name in enumerate(("r", "g", "b")):
            columns[name] = pa.array(
                srgb_to_linear.srgb_to_linear(channel=colors[valid, index]), type=pa.float32()
            )
    return columns
