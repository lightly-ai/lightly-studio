"""Stack the x, y, and z coordinate fields of a PointCloud2 message."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
from numpy.typing import NDArray

from lightly_studio.services.recording_service import read_point_cloud_field
from lightly_studio.services.recording_service.point_cloud_types import PointCloudLayout


def read_point_cloud_xyz(
    data: bytes, fields: Mapping[str, object], layout: PointCloudLayout
) -> NDArray[np.float32]:
    """Stack the x, y, and z fields into an (N, 3) float32 array.

    N is the number of points in the message.

    Args:
        data: The raw PointCloud2 data buffer.
        fields: A map of field name to the PointField describing it. Must contain
            the x, y, and z fields.
        layout: The byte layout shared by every field of the message.

    Returns:
        The stacked coordinates of shape (N, 3).
    """
    points = [
        read_point_cloud_field.read_point_cloud_field(data=data, field=fields[name], layout=layout)
        for name in ("x", "y", "z")
    ]
    return np.column_stack(points).astype(np.float32)
