from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from lightly_studio.core.mcap import camera_info
from lightly_studio.core.mcap.errors import McapAccessError

CAMERA_MATRIX = [600.0, 0.0, 320.0, 0.0, 600.0, 240.0, 0.0, 0.0, 1.0]


def _ros_camera_info() -> Any:
    """Returns a message shaped like a decoded `sensor_msgs/msg/CameraInfo`."""
    return SimpleNamespace(
        header=SimpleNamespace(frame_id="cam_front_optical"),
        height=480,
        width=640,
        distortion_model="plumb_bob",
        d=[0.1, 0.01],
        k=CAMERA_MATRIX,
    )


def _foxglove_camera_calibration() -> Any:
    """Returns a message shaped like a decoded `foxglove.CameraCalibration`."""
    return SimpleNamespace(
        frame_id="cam_front_optical",
        height=480,
        width=640,
        distortion_model="plumb_bob",
        D=[0.1, 0.01],
        K=CAMERA_MATRIX,
    )


def test_from_decoded_message__ros() -> None:
    intrinsics = camera_info.from_decoded_message(_ros_camera_info())

    assert intrinsics.width == 640
    assert intrinsics.height == 480
    assert intrinsics.camera_matrix == tuple(CAMERA_MATRIX)
    assert intrinsics.frame_id == "cam_front_optical"
    assert intrinsics.distortion_model == "plumb_bob"
    assert intrinsics.distortion_coefficients == (0.1, 0.01)


def test_from_decoded_message__foxglove() -> None:
    intrinsics = camera_info.from_decoded_message(_foxglove_camera_calibration())

    assert intrinsics.width == 640
    assert intrinsics.height == 480
    assert intrinsics.camera_matrix == tuple(CAMERA_MATRIX)
    assert intrinsics.frame_id == "cam_front_optical"


def test_from_decoded_message__json() -> None:
    message = {"width": 640, "height": 480, "K": CAMERA_MATRIX, "frame_id": "cam_front_optical"}

    intrinsics = camera_info.from_decoded_message(message)

    assert intrinsics.camera_matrix == tuple(CAMERA_MATRIX)
    assert intrinsics.frame_id == "cam_front_optical"
    assert intrinsics.distortion_model is None
    assert intrinsics.distortion_coefficients == ()


def test_from_decoded_message__no_frame_id() -> None:
    message = {"width": 640, "height": 480, "K": CAMERA_MATRIX}

    assert camera_info.from_decoded_message(message).frame_id is None


def test_from_decoded_message__no_camera_matrix() -> None:
    with pytest.raises(McapAccessError, match="has no field 'k', 'K'"):
        camera_info.from_decoded_message({"width": 640, "height": 480})


def test_from_decoded_message__incomplete_camera_matrix() -> None:
    message = {"width": 640, "height": 480, "K": [600.0, 0.0, 320.0]}

    with pytest.raises(McapAccessError, match=r"Camera matrix has 3 values, expected 9\."):
        camera_info.from_decoded_message(message)
