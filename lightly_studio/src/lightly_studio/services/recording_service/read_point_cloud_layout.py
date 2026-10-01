"""Read and validate the byte layout of a PointCloud2 message."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

from lightly_studio.core.mcap.errors import McapAccessError
from lightly_studio.services.recording_service import point_cloud_value
from lightly_studio.services.recording_service.point_cloud_types import PointCloudLayout


def read_point_cloud_layout(
    message: object,
) -> tuple[PointCloudLayout, bytes, dict[str, object]]:
    """Read the byte layout, data buffer, and field map of a PointCloud2 message.

    Args:
        message: A decoded PointCloud2 ROS message or an equivalent mapping.

    Returns:
        The point-cloud layout, its raw data buffer, and a map of field name to
        the PointField describing it.

    Raises:
        McapAccessError: If the message declares row or point dimensions that
            cannot form a valid point buffer, or misses required coordinate fields.
    """
    width = int(point_cloud_value.get_value(value=message, name="width"))
    height = int(point_cloud_value.get_value(value=message, name="height"))
    point_step = int(point_cloud_value.get_value(value=message, name="point_step"))
    row_step = int(point_cloud_value.get_value(value=message, name="row_step"))
    data = bytes(point_cloud_value.get_value(value=message, name="data"))
    fields = {
        str(point_cloud_value.get_value(value=field, name="name")): field
        for field in point_cloud_value.get_value(value=message, name="fields")
    }
    _validate_layout(
        width=width, height=height, point_step=point_step, row_step=row_step, data=data
    )
    _validate_required_fields(fields=fields)
    endian: Literal[">", "<"] = (
        ">" if bool(point_cloud_value.get_value(value=message, name="is_bigendian")) else "<"
    )
    layout = PointCloudLayout(
        width=width, height=height, point_step=point_step, row_step=row_step, endian=endian
    )
    return layout, data, fields


def _validate_layout(width: int, height: int, point_step: int, row_step: int, data: bytes) -> None:
    """Reject dimensions that cannot form a valid strided view over the data."""
    fits_points = row_step >= width * point_step
    fits_rows = len(data) >= row_step * height
    if width < 0 or height < 0 or point_step <= 0 or not fits_points or not fits_rows:
        raise McapAccessError("Point cloud has invalid row or point data dimensions.")


def _validate_required_fields(fields: Mapping[str, object]) -> None:
    """Ensure the x, y, and z coordinate fields are present."""
    missing = sorted(name for name in ("x", "y", "z") if name not in fields)
    if missing:
        raise McapAccessError(f"Point cloud is missing required fields: {', '.join(missing)}.")
