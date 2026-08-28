"""Decode ROS 2 PointCloud2 messages into render-ready points."""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

_DATATYPE_FORMATS = {
    1: "i1",
    2: "u1",
    3: "i2",
    4: "u2",
    5: "i4",
    6: "u4",
    7: "f4",
    8: "f8",
}


def decode_point_cloud2(message: Any) -> NDArray[np.float32]:
    """Decode a PointCloud2 message into finite XYZI float32 points."""
    fields = {field.name: field for field in message.fields}
    coordinate_names = ("x", "y", "z")
    missing = [name for name in coordinate_names if name not in fields]
    if missing:
        raise ValueError(f"Point cloud is missing required fields: {', '.join(missing)}")

    intensity_name = _intensity_name(fields=fields)
    selected_names = (*coordinate_names, *([intensity_name] if intensity_name else []))
    dtype = _structured_dtype(
        fields=fields,
        names=selected_names,
        point_step=message.point_step,
        big_endian=message.is_bigendian,
    )
    structured: NDArray[Any] = np.ndarray(
        shape=(message.height, message.width),
        dtype=dtype,
        buffer=message.data,
        strides=(message.row_step, message.point_step),
    ).reshape(-1)
    points = _stack_points(structured=structured, intensity_name=intensity_name)
    return np.asarray(points[np.isfinite(points[:, :3]).all(axis=1)], dtype=np.float32)


def _intensity_name(fields: dict[str, Any]) -> str | None:
    for name in ("intensity", "reflectivity"):
        if name in fields:
            return name
    return None


def _structured_dtype(
    fields: dict[str, Any],
    names: tuple[str, ...],
    point_step: int,
    big_endian: bool,
) -> np.dtype[Any]:
    formats = [_numpy_format(field=fields[name], big_endian=big_endian) for name in names]
    offsets = [fields[name].offset for name in names]
    return np.dtype(
        {"names": list(names), "formats": formats, "offsets": offsets, "itemsize": point_step}
    )


def _numpy_format(field: Any, big_endian: bool) -> str:
    if field.count != 1:
        raise ValueError(f"Point field '{field.name}' must contain one scalar value.")
    try:
        value_format = _DATATYPE_FORMATS[field.datatype]
    except KeyError as error:
        raise ValueError(
            f"Point field '{field.name}' has unsupported datatype {field.datatype}."
        ) from error
    if value_format.endswith("1"):
        return value_format
    return (">" if big_endian else "<") + value_format


def _stack_points(structured: NDArray[Any], intensity_name: str | None) -> NDArray[np.float32]:
    intensity = (
        structured[intensity_name]
        if intensity_name is not None
        else np.zeros(len(structured), dtype=np.float32)
    )
    return np.column_stack((structured["x"], structured["y"], structured["z"], intensity)).astype(
        np.float32
    )
