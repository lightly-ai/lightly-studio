"""Interpolate 3D cuboid poses between two ticks."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

Vector3 = tuple[float, float, float]
QuaternionXYZW = tuple[float, float, float, float]

# Above this dot product, slerp is unstable, so normalized lerp is used.
_NLERP_DOT_THRESHOLD = 0.9995


@dataclass(frozen=True)
class CuboidPose:
    """Center, size and rotation (unit quaternion x, y, z, w) of a cuboid."""

    center: Vector3
    size: Vector3
    rotation: QuaternionXYZW


@dataclass(frozen=True)
class TickPosition:
    """Position and timestamp of a tick in its sequence."""

    seq_number: int
    timestamp_ns: int | None


def gap_alphas(ticks: Sequence[TickPosition]) -> list[float]:
    """Return the weight of each tick strictly between the first and the last tick.

    Uses the timestamps if they strictly increase, else the sequence positions.
    """
    timestamps = [tick.timestamp_ns for tick in ticks if tick.timestamp_ns is not None]
    if len(timestamps) == len(ticks) and _strictly_increasing(values=timestamps):
        positions = [float(t) for t in timestamps]
    else:
        positions = [float(tick.seq_number) for tick in ticks]
    start, end = positions[0], positions[-1]
    return [(position - start) / (end - start) for position in positions[1:-1]]


def interpolate_pose(start: CuboidPose, end: CuboidPose, alpha: float) -> CuboidPose:
    """Interpolate center and size linearly and the rotation with slerp."""
    return CuboidPose(
        center=_lerp_vector(start=start.center, end=end.center, alpha=alpha),
        size=_lerp_vector(start=start.size, end=end.size, alpha=alpha),
        rotation=slerp(start=start.rotation, end=end.rotation, alpha=alpha),
    )


def slerp(start: QuaternionXYZW, end: QuaternionXYZW, alpha: float) -> QuaternionXYZW:
    """Interpolate two unit quaternions along the shortest path."""
    dot = sum(a * b for a, b in zip(start, end))
    if dot < 0.0:
        end = (-end[0], -end[1], -end[2], -end[3])
        dot = -dot
    if dot > _NLERP_DOT_THRESHOLD:
        return _normalize(q=_lerp_quaternion(start=start, end=end, alpha=alpha))
    theta = math.acos(dot)
    sin_theta = math.sin(theta)
    weight_start = math.sin((1.0 - alpha) * theta) / sin_theta
    weight_end = math.sin(alpha * theta) / sin_theta
    q = (
        weight_start * start[0] + weight_end * end[0],
        weight_start * start[1] + weight_end * end[1],
        weight_start * start[2] + weight_end * end[2],
        weight_start * start[3] + weight_end * end[3],
    )
    return _normalize(q=q)


def _strictly_increasing(values: Sequence[int]) -> bool:
    return all(a < b for a, b in zip(values, values[1:]))


def _lerp_vector(start: Vector3, end: Vector3, alpha: float) -> Vector3:
    return (
        start[0] + alpha * (end[0] - start[0]),
        start[1] + alpha * (end[1] - start[1]),
        start[2] + alpha * (end[2] - start[2]),
    )


def _lerp_quaternion(start: QuaternionXYZW, end: QuaternionXYZW, alpha: float) -> QuaternionXYZW:
    return (
        start[0] + alpha * (end[0] - start[0]),
        start[1] + alpha * (end[1] - start[1]),
        start[2] + alpha * (end[2] - start[2]),
        start[3] + alpha * (end[3] - start[3]),
    )


def _normalize(q: QuaternionXYZW) -> QuaternionXYZW:
    norm = math.hypot(*q)
    return (q[0] / norm, q[1] / norm, q[2] / norm, q[3] / norm)
