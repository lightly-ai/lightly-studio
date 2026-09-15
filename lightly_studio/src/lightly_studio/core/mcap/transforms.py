"""Static transforms between the coordinate frames of a recording."""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence
from typing import Any

import numpy as np
from numpy.typing import NDArray

from lightly_studio.core.mcap import message_fields
from lightly_studio.core.mcap.errors import TransformNotFoundError
from lightly_studio.core.mcap.type_definitions import StaticTransform

_TRANSFORMS_FIELDS = ("transforms",)
_TRANSFORM_FIELDS = ("transform",)
_PARENT_FRAME_ID_FIELDS = ("parent_frame_id",)
_CHILD_FRAME_ID_FIELDS = ("child_frame_id",)
_HEADER_FIELDS = ("header",)
_FRAME_ID_FIELDS = ("frame_id",)
_TRANSLATION_FIELDS = ("translation",)
_ROTATION_FIELDS = ("rotation",)


class TransformTree:
    """Composes the transforms between the coordinate frames of a recording.

    The tree treats every transform as an undirected edge between two frames, so it
    can look up transforms in both directions and across several edges.
    """

    def __init__(self, transforms: Sequence[StaticTransform]) -> None:
        """Builds the tree from a list of transforms.

        Args:
            transforms: The transforms to compose, for example the edges published on
                `/tf_static`. A later transform between the same two frames replaces an
                earlier one.
        """
        self._matrix_by_edge: dict[tuple[str, str], NDArray[np.float64]] = {}
        self._neighbor_frame_ids: dict[str, set[str]] = {}
        for transform in transforms:
            self._add(transform)

    @property
    def frame_ids(self) -> frozenset[str]:
        """The frames the tree knows about."""
        return frozenset(self._neighbor_frame_ids)

    def lookup(self, target_frame_id: str, source_frame_id: str) -> NDArray[np.float64]:
        """Returns the transform between two frames.

        Args:
            target_frame_id: The frame to map points to.
            source_frame_id: The frame to map points from.

        Returns:
            The 4x4 homogeneous transform that maps points from the source frame to the
            target frame.

        Raises:
            TransformNotFoundError: If no chain of transforms connects the two frames.
        """
        path = self._find_path(target_frame_id=target_frame_id, source_frame_id=source_frame_id)
        if path is None:
            raise TransformNotFoundError(
                f"No static transform connects frame '{source_frame_id}' to '{target_frame_id}'."
            )

        matrix = np.eye(4, dtype=np.float64)
        for from_frame_id, to_frame_id in zip(path[:-1], path[1:]):
            matrix = self._matrix_by_edge[(to_frame_id, from_frame_id)] @ matrix
        return matrix

    def _add(self, transform: StaticTransform) -> None:
        """Adds a transform as an edge that can be traversed in both directions."""
        parent = transform.parent_frame_id
        child = transform.child_frame_id
        matrix = to_matrix(transform)
        self._matrix_by_edge[(parent, child)] = matrix
        self._matrix_by_edge[(child, parent)] = np.linalg.inv(matrix)
        self._neighbor_frame_ids.setdefault(parent, set()).add(child)
        self._neighbor_frame_ids.setdefault(child, set()).add(parent)

    def _find_path(self, target_frame_id: str, source_frame_id: str) -> list[str] | None:
        """Returns the shortest chain of frames from the source to the target frame.

        Args:
            target_frame_id: The frame to map points to.
            source_frame_id: The frame to map points from.

        Returns:
            The frames to traverse, starting at the source and ending at the target
            frame, or `None` if the frames are not connected.
        """
        if source_frame_id not in self._neighbor_frame_ids:
            return None
        if source_frame_id == target_frame_id:
            return [source_frame_id]

        paths = deque([[source_frame_id]])
        visited = {source_frame_id}
        while paths:
            path = paths.popleft()
            for neighbor in sorted(self._neighbor_frame_ids[path[-1]]):
                if neighbor in visited:
                    continue
                if neighbor == target_frame_id:
                    return [*path, neighbor]
                visited.add(neighbor)
                paths.append([*path, neighbor])
        return None


def from_decoded_message(decoded_message: Any, log_time_ns: int) -> list[StaticTransform]:
    """Extracts the transforms from a decoded transform message.

    Reads `tf2_msgs/msg/TFMessage` and its Foxglove equivalents
    `foxglove.FrameTransforms` and `foxglove.FrameTransform`, which name the same
    values differently.

    Args:
        decoded_message: A decoded transform message, holding either a single transform
            or a list of them.
        log_time_ns: The time the message was logged, in nanoseconds.

    Returns:
        One transform per edge in the message.

    Raises:
        McapAccessError: If the message does not hold transforms.
    """
    transforms = message_fields.get_field(decoded_message, _TRANSFORMS_FIELDS)
    if transforms is None:
        return [_transform(decoded_message, log_time_ns=log_time_ns)]
    return [_transform(transform, log_time_ns=log_time_ns) for transform in transforms]


def to_matrix(transform: StaticTransform) -> NDArray[np.float64]:
    """Returns a transform as a homogeneous matrix.

    Args:
        transform: The transform to convert.

    Returns:
        The 4x4 homogeneous matrix that maps points from the child frame to the parent
        frame.
    """
    matrix = np.eye(4, dtype=np.float64)
    matrix[:3, :3] = _rotation_matrix(transform.rotation)
    matrix[:3, 3] = transform.translation
    return matrix


def _transform(decoded_transform: Any, log_time_ns: int) -> StaticTransform:
    """Extracts a single transform from a decoded message or one of its entries.

    Args:
        decoded_transform: A decoded transform, either a Foxglove `FrameTransform` or a
            ROS `TransformStamped`.
        log_time_ns: The time the transform was logged, in nanoseconds.

    Returns:
        The transform.

    Raises:
        McapAccessError: If the value does not hold a transform.
    """
    # ROS nests the translation and rotation in a `transform` field, Foxglove keeps them
    # on the transform itself.
    pose = message_fields.get_field(decoded_transform, _TRANSFORM_FIELDS)
    if pose is None:
        pose = decoded_transform

    child_frame_id = message_fields.require_field(decoded_transform, _CHILD_FRAME_ID_FIELDS)
    return StaticTransform(
        parent_frame_id=_parent_frame_id(decoded_transform),
        child_frame_id=str(child_frame_id),
        translation=_vector(message_fields.require_field(pose, _TRANSLATION_FIELDS)),
        rotation=_quaternion(message_fields.require_field(pose, _ROTATION_FIELDS)),
        log_time_ns=log_time_ns,
    )


def _parent_frame_id(decoded_transform: Any) -> str:
    """Returns the parent frame of a decoded transform.

    ROS carries the parent frame in the header, Foxglove on the transform itself.

    Args:
        decoded_transform: A decoded transform.

    Returns:
        The parent frame id.

    Raises:
        McapAccessError: If the transform does not name a parent frame.
    """
    parent_frame_id = message_fields.get_field(decoded_transform, _PARENT_FRAME_ID_FIELDS)
    if parent_frame_id is None:
        header = message_fields.require_field(decoded_transform, _HEADER_FIELDS)
        parent_frame_id = message_fields.require_field(header, _FRAME_ID_FIELDS)
    return str(parent_frame_id)


def _vector(decoded_vector: Any) -> tuple[float, float, float]:
    """Returns a decoded vector as (x, y, z)."""
    return (
        float(message_fields.require_field(decoded_vector, ("x",))),
        float(message_fields.require_field(decoded_vector, ("y",))),
        float(message_fields.require_field(decoded_vector, ("z",))),
    )


def _quaternion(decoded_quaternion: Any) -> tuple[float, float, float, float]:
    """Returns a decoded quaternion as (x, y, z, w)."""
    return (
        float(message_fields.require_field(decoded_quaternion, ("x",))),
        float(message_fields.require_field(decoded_quaternion, ("y",))),
        float(message_fields.require_field(decoded_quaternion, ("z",))),
        float(message_fields.require_field(decoded_quaternion, ("w",))),
    )


def _rotation_matrix(rotation: tuple[float, float, float, float]) -> NDArray[np.float64]:
    """Returns the rotation matrix of a quaternion.

    Args:
        rotation: The rotation as a quaternion (x, y, z, w). Normalized before use, so
            that a quaternion stored with limited precision still gives a rotation.

    Returns:
        The 3x3 rotation matrix.

    Raises:
        ValueError: If the quaternion has zero length.
    """
    quaternion = np.asarray(rotation, dtype=np.float64)
    norm = float(np.linalg.norm(quaternion))
    if norm == 0.0:
        raise ValueError("A rotation quaternion (x, y, z, w) must not be all zeros.")
    x, y, z, w = quaternion / norm
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ],
        dtype=np.float64,
    )
