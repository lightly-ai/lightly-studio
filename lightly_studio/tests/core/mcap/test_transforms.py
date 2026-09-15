from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from lightly_studio.core.mcap import transforms
from lightly_studio.core.mcap.errors import McapAccessError, TransformNotFoundError
from lightly_studio.core.mcap.transforms import TransformTree
from lightly_studio.core.mcap.type_definitions import StaticTransform

IDENTITY_ROTATION = (0.0, 0.0, 0.0, 1.0)
# A rotation by 90 degrees around the z axis.
QUARTER_TURN_ROTATION = (0.0, 0.0, 0.7071067811865476, 0.7071067811865476)


def _static_transform(
    parent_frame_id: str,
    child_frame_id: str,
    translation: tuple[float, float, float] = (0.0, 0.0, 0.0),
    rotation: tuple[float, float, float, float] = IDENTITY_ROTATION,
) -> StaticTransform:
    return StaticTransform(
        parent_frame_id=parent_frame_id,
        child_frame_id=child_frame_id,
        translation=translation,
        rotation=rotation,
        log_time_ns=1_000,
    )


class TestTransformTree:
    def test_frame_ids(self) -> None:
        tree = TransformTree([_static_transform(parent_frame_id="base", child_frame_id="cam")])

        assert tree.frame_ids == frozenset({"base", "cam"})

    def test_lookup(self) -> None:
        tree = TransformTree(
            [
                _static_transform(
                    parent_frame_id="base", child_frame_id="cam", translation=(1.0, 2.0, 3.0)
                )
            ]
        )

        matrix = tree.lookup(target_frame_id="base", source_frame_id="cam")

        assert np.allclose(matrix @ [0.0, 0.0, 0.0, 1.0], [1.0, 2.0, 3.0, 1.0])

    def test_lookup__reversed(self) -> None:
        tree = TransformTree(
            [
                _static_transform(
                    parent_frame_id="base", child_frame_id="cam", translation=(1.0, 2.0, 3.0)
                )
            ]
        )

        matrix = tree.lookup(target_frame_id="cam", source_frame_id="base")

        assert np.allclose(matrix @ [1.0, 2.0, 3.0, 1.0], [0.0, 0.0, 0.0, 1.0])

    def test_lookup__composed(self) -> None:
        tree = TransformTree(
            [
                _static_transform(
                    parent_frame_id="base",
                    child_frame_id="cam",
                    translation=(1.0, 0.0, 0.0),
                    rotation=QUARTER_TURN_ROTATION,
                ),
                _static_transform(
                    parent_frame_id="base", child_frame_id="lidar", translation=(0.0, 1.0, 0.0)
                ),
            ]
        )

        matrix = tree.lookup(target_frame_id="cam", source_frame_id="lidar")

        # The lidar origin sits 1 m to the left of the camera origin, which the camera
        # sees 1 m ahead of itself because it is turned by 90 degrees.
        assert np.allclose(matrix @ [0.0, 0.0, 0.0, 1.0], [1.0, 1.0, 0.0, 1.0])

    def test_lookup__same_frame(self) -> None:
        tree = TransformTree([_static_transform(parent_frame_id="base", child_frame_id="cam")])

        matrix = tree.lookup(target_frame_id="cam", source_frame_id="cam")

        assert np.allclose(matrix, np.eye(4))

    def test_lookup__unknown_frame(self) -> None:
        tree = TransformTree([_static_transform(parent_frame_id="base", child_frame_id="cam")])

        with pytest.raises(
            TransformNotFoundError,
            match=r"No static transform connects frame 'lidar' to 'cam'\.",
        ):
            tree.lookup(target_frame_id="cam", source_frame_id="lidar")

    def test_lookup__disconnected_frames(self) -> None:
        tree = TransformTree(
            [
                _static_transform(parent_frame_id="base", child_frame_id="cam"),
                _static_transform(parent_frame_id="map", child_frame_id="odom"),
            ]
        )

        with pytest.raises(TransformNotFoundError):
            tree.lookup(target_frame_id="odom", source_frame_id="cam")

    def test_lookup__no_transforms(self) -> None:
        with pytest.raises(TransformNotFoundError):
            TransformTree([]).lookup(target_frame_id="cam", source_frame_id="lidar")


def test_from_decoded_message__ros() -> None:
    message = SimpleNamespace(
        transforms=[
            SimpleNamespace(
                header=SimpleNamespace(frame_id="base"),
                child_frame_id="cam",
                transform=SimpleNamespace(
                    translation=SimpleNamespace(x=1.0, y=2.0, z=3.0),
                    rotation=SimpleNamespace(x=0.0, y=0.0, z=0.0, w=1.0),
                ),
            )
        ]
    )

    static_transforms = transforms.from_decoded_message(message, log_time_ns=42)

    assert static_transforms == [
        StaticTransform(
            parent_frame_id="base",
            child_frame_id="cam",
            translation=(1.0, 2.0, 3.0),
            rotation=IDENTITY_ROTATION,
            log_time_ns=42,
        )
    ]


def test_from_decoded_message__foxglove() -> None:
    message: Any = {
        "transforms": [
            {
                "parent_frame_id": "base",
                "child_frame_id": "cam",
                "translation": {"x": 1.0, "y": 2.0, "z": 3.0},
                "rotation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
            }
        ]
    }

    static_transforms = transforms.from_decoded_message(message, log_time_ns=42)

    assert static_transforms == [
        StaticTransform(
            parent_frame_id="base",
            child_frame_id="cam",
            translation=(1.0, 2.0, 3.0),
            rotation=IDENTITY_ROTATION,
            log_time_ns=42,
        )
    ]


def test_from_decoded_message__single_transform() -> None:
    message: Any = {
        "parent_frame_id": "base",
        "child_frame_id": "cam",
        "translation": {"x": 0.0, "y": 0.0, "z": 0.0},
        "rotation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
    }

    static_transforms = transforms.from_decoded_message(message, log_time_ns=42)

    assert len(static_transforms) == 1
    assert static_transforms[0].child_frame_id == "cam"


def test_from_decoded_message__no_transform() -> None:
    with pytest.raises(McapAccessError, match="has no field 'child_frame_id'"):
        transforms.from_decoded_message({"parent_frame_id": "base"}, log_time_ns=42)


def test_to_matrix() -> None:
    transform = _static_transform(
        parent_frame_id="base",
        child_frame_id="cam",
        translation=(1.0, 0.0, 0.0),
        rotation=QUARTER_TURN_ROTATION,
    )

    matrix = transforms.to_matrix(transform)

    assert np.allclose(
        matrix,
        [
            [0.0, -1.0, 0.0, 1.0],
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ],
    )


def test_rotation_matrix__unnormalized_quaternion() -> None:
    matrix = transforms._rotation_matrix((0.0, 0.0, 0.5, 0.5))

    assert np.allclose(matrix, [[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])


def test_rotation_matrix__zero_quaternion() -> None:
    with pytest.raises(ValueError, match="must not be all zeros"):
        transforms._rotation_matrix((0.0, 0.0, 0.0, 0.0))
