from __future__ import annotations

import math

import pytest

from lightly_studio.core.mcap.errors import TransformNotFoundError
from lightly_studio.core.mcap.type_definitions import StaticTransform
from lightly_studio.services.recording_service.world_poses import Pose, WorldPoses

SECOND_NS = 1_000_000_000


def test_world_frame_of__walks_up_to_the_root() -> None:
    world = WorldPoses(
        static_transforms=[_edge(parent="base_link", child="lidar", yaw_deg=0.0)],
        dynamic_transforms=[_edge(parent="odom", child="base_link", yaw_deg=0.0)],
    )

    assert world.world_frame_of("lidar") == "odom"
    assert world.world_frame_of("base_link") == "odom"
    assert world.world_frame_of("odom") == "odom"
    assert world.world_frame_of("unknown") is None


def test_hold_in_world__follows_the_moving_frame() -> None:
    world = _rotating_frame()
    pose = Pose(position=(10.0, 0.0, 0.0), rotation=_yaw(0.0))

    held = world.hold_in_world(pose=pose, frame_id="base_link", from_ns=0, to_ns=3 * SECOND_NS)

    assert held.position == pytest.approx((0.0, -10.0, 0.0), abs=1e-9)
    assert _yaw_deg(held.rotation) == pytest.approx(-90.0)


def test_hold_in_world__keeps_a_pose_without_transforms() -> None:
    world = WorldPoses(static_transforms=[], dynamic_transforms=[])
    pose = Pose(position=(1.0, 2.0, 3.0), rotation=_yaw(30.0))

    assert world.hold_in_world(pose=pose, frame_id="base_link", from_ns=0, to_ns=SECOND_NS) == pose


def test_map_pose__to_the_world_frame() -> None:
    world = _rotating_frame()

    mapped = world.map_pose(
        pose=Pose(position=(0.0, -10.0, 0.0), rotation=_yaw(-90.0)),
        source_frame_id="base_link",
        target_frame_id="odom",
        timestamp_ns=2 * SECOND_NS,
    )

    assert mapped.position == pytest.approx((10.0, 0.0, 0.0), abs=1e-9)
    assert _yaw_deg(mapped.rotation) == pytest.approx(0.0, abs=1e-9)


def test_map_pose__uses_the_closest_edge_out_of_the_window() -> None:
    # The first edge is 1 s after the capture time, out of the 100 ms window.
    world = WorldPoses(
        static_transforms=[],
        dynamic_transforms=[
            _edge(parent="odom", child="base_link", yaw_deg=90.0, timestamp_ns=SECOND_NS),
            _edge(parent="odom", child="base_link", yaw_deg=0.0, timestamp_ns=3 * SECOND_NS),
        ],
    )

    mapped = world.map_pose(
        pose=Pose(position=(10.0, 0.0, 0.0), rotation=_yaw(0.0)),
        source_frame_id="base_link",
        target_frame_id="odom",
        timestamp_ns=0,
    )

    assert mapped.position == pytest.approx((0.0, 10.0, 0.0), abs=1e-9)
    assert _yaw_deg(mapped.rotation) == pytest.approx(90.0)


def test_map_pose__ignores_a_zero_quaternion_on_another_frame() -> None:
    world = WorldPoses(
        static_transforms=[],
        dynamic_transforms=[
            _edge(parent="odom", child="base_link", yaw_deg=90.0),
            _zero_rotation_edge(parent="odom", child="other_vehicle", timestamp_ns=0),
        ],
    )

    mapped = world.map_pose(
        pose=Pose(position=(10.0, 0.0, 0.0), rotation=_yaw(0.0)),
        source_frame_id="base_link",
        target_frame_id="odom",
        timestamp_ns=0,
    )

    assert mapped.position == pytest.approx((0.0, 10.0, 0.0), abs=1e-9)


def test_map_pose__uses_the_closest_edge_with_a_rotation() -> None:
    world = WorldPoses(
        static_transforms=[],
        dynamic_transforms=[
            _edge(parent="odom", child="base_link", yaw_deg=90.0, timestamp_ns=0),
            _zero_rotation_edge(parent="odom", child="base_link", timestamp_ns=SECOND_NS),
        ],
    )

    mapped = world.map_pose(
        pose=Pose(position=(10.0, 0.0, 0.0), rotation=_yaw(0.0)),
        source_frame_id="base_link",
        target_frame_id="odom",
        timestamp_ns=SECOND_NS,
    )

    assert mapped.position == pytest.approx((0.0, 10.0, 0.0), abs=1e-9)


def test_map_pose__raises_if_the_frame_has_only_zero_quaternions() -> None:
    world = WorldPoses(
        static_transforms=[],
        dynamic_transforms=[_zero_rotation_edge(parent="odom", child="base_link", timestamp_ns=0)],
    )

    with pytest.raises(TransformNotFoundError):
        world.map_pose(
            pose=Pose(position=(10.0, 0.0, 0.0), rotation=_yaw(0.0)),
            source_frame_id="base_link",
            target_frame_id="odom",
            timestamp_ns=0,
        )


def test_hold_in_world__from_a_time_before_the_first_edge() -> None:
    world = WorldPoses(
        static_transforms=[],
        dynamic_transforms=[
            _edge(parent="odom", child="base_link", yaw_deg=yaw, timestamp_ns=second * SECOND_NS)
            for second, yaw in ((1, 0.0), (2, 90.0))
        ],
    )
    pose = Pose(position=(10.0, 0.0, 0.0), rotation=_yaw(0.0))

    held = world.hold_in_world(pose=pose, frame_id="base_link", from_ns=0, to_ns=2 * SECOND_NS)

    assert held.position == pytest.approx((0.0, -10.0, 0.0), abs=1e-9)
    assert _yaw_deg(held.rotation) == pytest.approx(-90.0)


def _rotating_frame() -> WorldPoses:
    """`base_link` is aligned with `odom` until 1 s and rotated by 90 degrees from 2 s."""
    return WorldPoses(
        static_transforms=[],
        dynamic_transforms=[
            _edge(parent="odom", child="base_link", yaw_deg=yaw, timestamp_ns=second * SECOND_NS)
            for second, yaw in ((0, 0.0), (1, 0.0), (2, 90.0), (3, 90.0))
        ],
    )


def _edge(parent: str, child: str, yaw_deg: float, timestamp_ns: int = 0) -> StaticTransform:
    return StaticTransform(
        parent_frame_id=parent,
        child_frame_id=child,
        translation=(0.0, 0.0, 0.0),
        rotation=_yaw(yaw_deg),
        timestamp_ns=timestamp_ns,
    )


def _zero_rotation_edge(parent: str, child: str, timestamp_ns: int) -> StaticTransform:
    return StaticTransform(
        parent_frame_id=parent,
        child_frame_id=child,
        translation=(0.0, 0.0, 0.0),
        rotation=(0.0, 0.0, 0.0, 0.0),
        timestamp_ns=timestamp_ns,
    )


def _yaw(degrees: float) -> tuple[float, float, float, float]:
    half = math.radians(degrees) / 2
    return (0.0, 0.0, math.sin(half), math.cos(half))


def _yaw_deg(rotation: tuple[float, float, float, float]) -> float:
    qx, qy, qz, qw = rotation
    return math.degrees(math.atan2(2 * (qw * qz + qx * qy), 1 - 2 * (qy * qy + qz * qz)))
