from __future__ import annotations

import math

import pytest

from lightly_studio.models.annotation.cuboid_3d import Cuboid3DCreate
from lightly_studio.services.object_track_service import pose_interpolation
from lightly_studio.services.object_track_service.pose_interpolation import CuboidPose, TickPosition

_SIN_45 = math.sin(math.pi / 4)


def test_gap_alphas__uses_timestamps() -> None:
    ticks = [
        TickPosition(seq_number=0, timestamp_ns=0),
        TickPosition(seq_number=1, timestamp_ns=10),
        TickPosition(seq_number=2, timestamp_ns=40),
        TickPosition(seq_number=3, timestamp_ns=100),
    ]
    assert pose_interpolation.gap_alphas(ticks=ticks) == pytest.approx([0.1, 0.4])


def test_gap_alphas__missing_timestamp_uses_seq_number() -> None:
    ticks = [
        TickPosition(seq_number=0, timestamp_ns=0),
        TickPosition(seq_number=1, timestamp_ns=None),
        TickPosition(seq_number=2, timestamp_ns=40),
        TickPosition(seq_number=3, timestamp_ns=100),
    ]
    assert pose_interpolation.gap_alphas(ticks=ticks) == pytest.approx([1 / 3, 2 / 3])


def test_gap_alphas__non_increasing_timestamps_use_seq_number() -> None:
    ticks = [
        TickPosition(seq_number=0, timestamp_ns=50),
        TickPosition(seq_number=1, timestamp_ns=50),
        TickPosition(seq_number=2, timestamp_ns=50),
    ]
    assert pose_interpolation.gap_alphas(ticks=ticks) == pytest.approx([0.5])


def test_gap_alphas__adjacent_anchors() -> None:
    ticks = [
        TickPosition(seq_number=0, timestamp_ns=0),
        TickPosition(seq_number=1, timestamp_ns=10),
    ]
    assert pose_interpolation.gap_alphas(ticks=ticks) == []


def test_interpolate_pose__lerps_center_and_size() -> None:
    start = CuboidPose(center=(0.0, 0.0, 0.0), size=(2.0, 1.0, 1.0), rotation=(0.0, 0.0, 0.0, 1.0))
    end = CuboidPose(center=(10.0, 20.0, -4.0), size=(4.0, 3.0, 1.0), rotation=(0.0, 0.0, 0.0, 1.0))

    result = pose_interpolation.interpolate_pose(start=start, end=end, alpha=0.25)

    assert result.center == pytest.approx((2.5, 5.0, -1.0))
    assert result.size == pytest.approx((2.5, 1.5, 1.0))
    assert result.rotation == pytest.approx((0.0, 0.0, 0.0, 1.0))


def test_interpolate_pose__result_passes_cuboid_validation() -> None:
    angle = 0.001
    start = CuboidPose(center=(0.0, 0.0, 0.0), size=(1.0, 1.0, 1.0), rotation=(0.0, 0.0, 0.0, 1.0))
    end = CuboidPose(
        center=(0.0, 0.0, 0.0),
        size=(1.0, 1.0, 1.0),
        rotation=(0.0, 0.0, math.sin(angle / 2), math.cos(angle / 2)),
    )

    result = pose_interpolation.interpolate_pose(start=start, end=end, alpha=0.5)

    assert math.hypot(*result.rotation) == pytest.approx(1.0, abs=1e-9)
    qx, qy, qz, qw = result.rotation
    Cuboid3DCreate(
        frame_id="odom",
        px=0.0,
        py=0.0,
        pz=0.0,
        qx=qx,
        qy=qy,
        qz=qz,
        qw=qw,
        sx=1.0,
        sy=1.0,
        sz=1.0,
    )


def test_slerp__quarter_turn_about_z() -> None:
    result = pose_interpolation.slerp(
        start=(0.0, 0.0, 0.0, 1.0), end=(0.0, 0.0, _SIN_45, _SIN_45), alpha=0.5
    )
    assert result == pytest.approx((0.0, 0.0, 0.38268343, 0.92387953))


def test_slerp__takes_shortest_path() -> None:
    result = pose_interpolation.slerp(
        start=(0.0, 0.0, 0.0, 1.0), end=(0.0, 0.0, -_SIN_45, -_SIN_45), alpha=0.5
    )
    assert result == pytest.approx((0.0, 0.0, 0.38268343, 0.92387953))


def test_slerp__sign_flipped_identity_stays_constant() -> None:
    result = pose_interpolation.slerp(
        start=(0.0, 0.0, 0.0, 1.0), end=(0.0, 0.0, 0.0, -1.0), alpha=0.3
    )
    assert result == pytest.approx((0.0, 0.0, 0.0, 1.0))
