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
        timestamp_ns=1_000,
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

    def test_lookup__reparented_child(self) -> None:
        tree = TransformTree(
            [
                _static_transform(
                    parent_frame_id="base", child_frame_id="cam", translation=(1.0, 0.0, 0.0)
                ),
                _static_transform(
                    parent_frame_id="map", child_frame_id="cam", translation=(0.0, 1.0, 0.0)
                ),
            ]
        )

        assert tree.frame_ids == frozenset({"map", "cam"})
        with pytest.raises(TransformNotFoundError):
            tree.lookup(target_frame_id="base", source_frame_id="cam")

        matrix = tree.lookup(target_frame_id="map", source_frame_id="cam")
        assert np.allclose(matrix @ [0.0, 0.0, 0.0, 1.0], [0.0, 1.0, 0.0, 1.0])


def test_frame_edges__ignores_the_pose() -> None:
    message = {
        "transforms": [
            {
                "header": {"frame_id": "map"},
                "child_frame_id": "base_link",
            }
        ]
    }

    assert transforms.frame_edges(message) == [("map", "base_link")]


def test_from_decoded_message__ros() -> None:
    message = SimpleNamespace(
        transforms=[
            SimpleNamespace(
                header=SimpleNamespace(frame_id="base", stamp=SimpleNamespace(sec=1, nanosec=5)),
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
            timestamp_ns=1_000_000_005,
        )
    ]


def test_from_decoded_message__foxglove() -> None:
    message: Any = {
        "transforms": [
            {
                "timestamp": {"sec": 2, "nsec": 7},
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
            timestamp_ns=2_000_000_007,
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


@pytest.mark.parametrize(
    "stamp_fields",
    [
        {},
        {"timestamp": {"sec": 0, "nsec": 0}},
        {"timestamp": {"nsec": 7}},
    ],
)
def test_from_decoded_message__capture_timestamp_falls_back_to_log_time(
    stamp_fields: dict[str, Any],
) -> None:
    message: Any = {
        **stamp_fields,
        "parent_frame_id": "base",
        "child_frame_id": "cam",
        "translation": {"x": 0.0, "y": 0.0, "z": 0.0},
        "rotation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
    }

    static_transforms = transforms.from_decoded_message(message, log_time_ns=42)

    assert static_transforms[0].timestamp_ns == 42


def test_from_decoded_message__no_transform() -> None:
    with pytest.raises(McapAccessError, match="has no field 'child_frame_id'"):
        transforms.from_decoded_message({"parent_frame_id": "base"}, log_time_ns=42)


@pytest.mark.parametrize(
    ("translation", "rotation"),
    [
        ((float("nan"), 0.0, 0.0), IDENTITY_ROTATION),
        ((float("inf"), 0.0, 0.0), IDENTITY_ROTATION),
        ((0.0, 0.0, 0.0), (0.0, 0.0, float("nan"), 1.0)),
        ((0.0, 0.0, 0.0), (0.0, 0.0, float("inf"), 1.0)),
    ],
)
def test_from_decoded_message__non_finite(
    translation: tuple[float, float, float], rotation: tuple[float, float, float, float]
) -> None:
    message: Any = {
        "parent_frame_id": "base",
        "child_frame_id": "cam",
        "translation": {"x": translation[0], "y": translation[1], "z": translation[2]},
        "rotation": {"x": rotation[0], "y": rotation[1], "z": rotation[2], "w": rotation[3]},
    }

    with pytest.raises(McapAccessError, match="non-finite translation or rotation"):
        transforms.from_decoded_message(message, log_time_ns=42)


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


def test_to_matrix__unnormalized_quaternion() -> None:
    transform = _static_transform(
        parent_frame_id="base",
        child_frame_id="cam",
        rotation=(0.0, 0.0, 0.5, 0.5),
    )

    matrix = transforms.to_matrix(transform)

    assert np.allclose(matrix[:3, :3], [[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])


def test_to_matrix__zero_quaternion() -> None:
    transform = _static_transform(
        parent_frame_id="base",
        child_frame_id="cam",
        rotation=(0.0, 0.0, 0.0, 0.0),
    )

    with pytest.raises(ValueError, match="zero norm"):
        transforms.to_matrix(transform)


def test_transform_pose() -> None:
    matrix = transforms.to_matrix(
        _static_transform(
            parent_frame_id="world",
            child_frame_id="base",
            translation=(1.0, 2.0, 3.0),
            rotation=QUARTER_TURN_ROTATION,
        )
    )

    position, rotation = transforms.transform_pose(
        matrix=matrix, position=(1.0, 0.0, 0.0), rotation=QUARTER_TURN_ROTATION
    )

    # The pose is turned by 90 degrees and moved, so that it faces backwards in the target.
    assert np.allclose(position, (1.0, 3.0, 3.0))
    # A half turn has w = 0, so the quaternion and its negation are both valid results.
    assert abs(np.dot(rotation, (0.0, 0.0, 1.0, 0.0))) == pytest.approx(1.0)


def test_transform_pose__identity_keeps_unnormalized_orientation_as_unit() -> None:
    position, rotation = transforms.transform_pose(
        matrix=np.eye(4), position=(1.0, 2.0, 3.0), rotation=(0.0, 0.0, 0.5, 0.5)
    )

    assert position == (1.0, 2.0, 3.0)
    assert np.allclose(rotation, QUARTER_TURN_ROTATION)


def test_transform_pose__zero_quaternion() -> None:
    with pytest.raises(ValueError, match="zero norm"):
        transforms.transform_pose(
            matrix=np.eye(4), position=(0.0, 0.0, 0.0), rotation=(0.0, 0.0, 0.0, 0.0)
        )


@pytest.mark.parametrize(
    "rotation",
    [
        (0.0, 0.0, 0.0, 1.0),
        (1.0, 0.0, 0.0, 0.0),
        (0.0, 1.0, 0.0, 0.0),
        (0.0, 0.0, 1.0, 0.0),
        (0.5, -0.5, 0.5, 0.5),
    ],
)
def test_transform_pose__identity_preserves_rotation(
    rotation: tuple[float, float, float, float],
) -> None:
    _, quaternion = transforms.transform_pose(
        matrix=np.eye(4), position=(0.0, 0.0, 0.0), rotation=rotation
    )

    # Half turns have w = 0, so the quaternion and its negation are both valid results.
    assert abs(np.dot(quaternion, rotation)) == pytest.approx(1.0)


def test_transform_pose__negative_w() -> None:
    _, quaternion = transforms.transform_pose(
        matrix=np.eye(4),
        position=(0.0, 0.0, 0.0),
        rotation=(0.0, 0.0, -0.7071067811865476, -0.7071067811865476),
    )

    assert np.allclose(quaternion, QUARTER_TURN_ROTATION)
