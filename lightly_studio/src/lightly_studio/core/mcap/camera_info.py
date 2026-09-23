"""Reading camera intrinsics from decoded camera info messages."""

from __future__ import annotations

from typing import Any

from lightly_studio.core.mcap import message_fields
from lightly_studio.core.mcap.errors import McapAccessError
from lightly_studio.core.mcap.type_definitions import CameraIntrinsics

CAMERA_MATRIX_SIZE = 9

_WIDTH_FIELDS = ("width",)
_HEIGHT_FIELDS = ("height",)
_CAMERA_MATRIX_FIELDS = ("k", "K")
_DISTORTION_FIELDS = ("d", "D")
_DISTORTION_MODEL_FIELDS = ("distortion_model",)
_HEADER_FIELDS = ("header",)
_FRAME_ID_FIELDS = ("frame_id",)


def from_decoded_message(decoded_message: Any) -> CameraIntrinsics:
    """Extracts the camera intrinsics from a decoded camera info message.

    Reads `sensor_msgs/msg/CameraInfo` and its Foxglove equivalent
    `foxglove.CameraCalibration`, which name the same values differently.

    Args:
        decoded_message: A decoded camera info message.

    Returns:
        The intrinsics of the camera.

    Raises:
        McapAccessError: If the message does not hold camera intrinsics.
    """
    camera_matrix = tuple(
        float(value)
        for value in message_fields.require_field(decoded_message, _CAMERA_MATRIX_FIELDS)
    )
    if len(camera_matrix) != CAMERA_MATRIX_SIZE:
        raise McapAccessError(
            f"Camera matrix has {len(camera_matrix)} values, expected {CAMERA_MATRIX_SIZE}."
        )

    distortion_model = message_fields.get_field(decoded_message, _DISTORTION_MODEL_FIELDS)
    distortion_coefficients = message_fields.get_field(decoded_message, _DISTORTION_FIELDS) or ()
    return CameraIntrinsics(
        width=int(message_fields.require_field(decoded_message, _WIDTH_FIELDS)),
        height=int(message_fields.require_field(decoded_message, _HEIGHT_FIELDS)),
        camera_matrix=camera_matrix,
        frame_id=_frame_id(decoded_message),
        distortion_model=None if distortion_model is None else str(distortion_model),
        distortion_coefficients=tuple(float(value) for value in distortion_coefficients),
    )


def _frame_id(decoded_message: Any) -> str | None:
    """Returns the coordinate frame of a decoded camera info message.

    ROS messages carry the frame in their header, Foxglove messages on the message
    itself.

    Args:
        decoded_message: A decoded camera info message.

    Returns:
        The frame id, or `None` if the message does not name one.
    """
    header = message_fields.get_field(decoded_message, _HEADER_FIELDS)
    frame_id = None if header is None else message_fields.get_field(header, _FRAME_ID_FIELDS)
    if frame_id is None:
        frame_id = message_fields.get_field(decoded_message, _FRAME_ID_FIELDS)
    return None if frame_id is None else str(frame_id)
