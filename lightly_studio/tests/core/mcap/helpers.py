"""Builds small MCAP files to read in the tests.

The fixtures use ROS 2 message definitions because they can be written without any
compiled schemas.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mcap.writer import Writer as RawWriter
from mcap_ros2.writer import Writer

CAMERA_VIDEO_TOPIC = "/cam/front/compressed_video"
CAMERA_INFO_TOPIC = "/cam/front/camera_info"
LIDAR_POINTS_TOPIC = "/lidar/points"
STATIC_TRANSFORM_TOPIC = "/tf_static"

CAMERA_FRAME_ID = "cam_front_optical"
LIDAR_FRAME_ID = "livox_front_left"
BASE_FRAME_ID = "base_link"

# The log times of the video frames, one frame every 100 ms. The frames at index 0 and
# 2 are keyframes.
VIDEO_LOG_TIMES_NS = (1_000_000_000, 1_100_000_000, 1_200_000_000, 1_300_000_000)
VIDEO_KEYFRAME_LOG_TIMES_NS = (1_000_000_000, 1_200_000_000)

LIDAR_LOG_TIMES_NS = (1_050_000_000, 1_250_000_000)
CAMERA_INFO_LOG_TIME_NS = 1_000_000_000
STATIC_TRANSFORM_LOG_TIME_NS = 900_000_000

CAMERA_MATRIX = (600.0, 0.0, 320.0, 0.0, 600.0, 240.0, 0.0, 0.0, 1.0)
IMAGE_WIDTH = 640
IMAGE_HEIGHT = 480

_HEADER_MSGDEF = """
================================================================================
MSG: std_msgs/Header
builtin_interfaces/Time stamp
string frame_id
"""

_COMPRESSED_VIDEO_MSGDEF = """
builtin_interfaces/Time timestamp
string frame_id
uint8[] data
string format
"""

_CAMERA_INFO_MSGDEF = (
    """
std_msgs/Header header
uint32 height
uint32 width
string distortion_model
float64[] d
float64[9] k
float64[9] r
float64[12] p
uint32 binning_x
uint32 binning_y
sensor_msgs/RegionOfInterest roi
"""
    + _HEADER_MSGDEF
    + """
================================================================================
MSG: sensor_msgs/RegionOfInterest
uint32 x_offset
uint32 y_offset
uint32 height
uint32 width
bool do_rectify
"""
)

_POINT_CLOUD_MSGDEF = (
    """
std_msgs/Header header
uint32 height
uint32 width
sensor_msgs/PointField[] fields
bool is_bigendian
uint32 point_step
uint32 row_step
uint8[] data
bool is_dense
"""
    + _HEADER_MSGDEF
    + """
================================================================================
MSG: sensor_msgs/PointField
string name
uint32 offset
uint8 datatype
uint32 count
"""
)

_TF_MESSAGE_MSGDEF = (
    """
geometry_msgs/TransformStamped[] transforms
================================================================================
MSG: geometry_msgs/TransformStamped
std_msgs/Header header
string child_frame_id
geometry_msgs/Transform transform
================================================================================
MSG: geometry_msgs/Transform
geometry_msgs/Vector3 translation
geometry_msgs/Quaternion rotation
================================================================================
MSG: geometry_msgs/Vector3
float64 x
float64 y
float64 z
================================================================================
MSG: geometry_msgs/Quaternion
float64 x
float64 y
float64 z
float64 w
"""
    + _HEADER_MSGDEF
)


def write_mcap(path: Path) -> Path:
    """Writes an indexed MCAP file with a camera, a lidar, and static transforms.

    Args:
        path: The path to write the file to.

    Returns:
        The path of the written file.
    """
    writer = Writer(output=str(path))
    video_schema = writer.register_msgdef(
        datatype="foxglove_msgs/msg/CompressedVideo", msgdef_text=_COMPRESSED_VIDEO_MSGDEF
    )
    camera_info_schema = writer.register_msgdef(
        datatype="sensor_msgs/msg/CameraInfo", msgdef_text=_CAMERA_INFO_MSGDEF
    )
    point_cloud_schema = writer.register_msgdef(
        datatype="sensor_msgs/msg/PointCloud2", msgdef_text=_POINT_CLOUD_MSGDEF
    )
    tf_schema = writer.register_msgdef(
        datatype="tf2_msgs/msg/TFMessage", msgdef_text=_TF_MESSAGE_MSGDEF
    )

    writer.write_message(
        topic=STATIC_TRANSFORM_TOPIC,
        schema=tf_schema,
        message=_static_transforms_message(),
        log_time=STATIC_TRANSFORM_LOG_TIME_NS,
    )
    writer.write_message(
        topic=CAMERA_INFO_TOPIC,
        schema=camera_info_schema,
        message=_camera_info_message(),
        log_time=CAMERA_INFO_LOG_TIME_NS,
    )
    for log_time_ns in VIDEO_LOG_TIMES_NS:
        writer.write_message(
            topic=CAMERA_VIDEO_TOPIC,
            schema=video_schema,
            message=_compressed_video_message(log_time_ns=log_time_ns),
            log_time=log_time_ns,
        )
    for log_time_ns in LIDAR_LOG_TIMES_NS:
        writer.write_message(
            topic=LIDAR_POINTS_TOPIC,
            schema=point_cloud_schema,
            message=_point_cloud_message(),
            log_time=log_time_ns,
        )
    writer.finish()
    return path


def write_unchunked_mcap(path: Path) -> Path:
    """Writes an MCAP file with a summary but no chunk index.

    Args:
        path: The path to write the file to.

    Returns:
        The path of the written file.
    """
    writer = RawWriter(output=str(path), use_chunking=False)
    writer.start()
    schema_id = writer.register_schema(name="empty", encoding="", data=b"")
    channel_id = writer.register_channel(
        topic=LIDAR_POINTS_TOPIC, message_encoding="", schema_id=schema_id
    )
    writer.add_message(
        channel_id=channel_id, log_time=LIDAR_LOG_TIMES_NS[0], data=b"", publish_time=0
    )
    writer.finish()
    return path


def write_mcap_with_undecodable_video(path: Path) -> Path:
    """Writes an MCAP whose video topic has no decoder.

    The schema name marks the topic as video, but its encoding is unknown, so no
    decoder factory can read the payloads and no keyframe can be detected.

    Args:
        path: The path to write the file to.

    Returns:
        The path of the written file.
    """
    with path.open("wb") as stream:
        writer = RawWriter(output=stream)
        writer.start()
        schema_id = writer.register_schema(
            name="foxglove_msgs/msg/CompressedVideo", encoding="unknown", data=b""
        )
        channel_id = writer.register_channel(
            topic=CAMERA_VIDEO_TOPIC, message_encoding="unknown", schema_id=schema_id
        )
        for log_time_ns in VIDEO_LOG_TIMES_NS:
            writer.add_message(
                channel_id=channel_id,
                log_time=log_time_ns,
                publish_time=log_time_ns,
                data=h265_keyframe(),
            )
        writer.finish()
    return path


def write_mcap_with_undecodable_camera_info(path: Path) -> Path:
    """Writes an MCAP whose camera info topic has no decoder.

    The topic's encoding is unknown, so no decoder factory can read its payloads.

    Args:
        path: The path to write the file to.

    Returns:
        The path of the written file.
    """
    with path.open("wb") as stream:
        writer = RawWriter(output=stream)
        writer.start()
        schema_id = writer.register_schema(
            name="sensor_msgs/msg/CameraInfo", encoding="unknown", data=b""
        )
        channel_id = writer.register_channel(
            topic=CAMERA_INFO_TOPIC, message_encoding="unknown", schema_id=schema_id
        )
        writer.add_message(
            channel_id=channel_id,
            log_time=CAMERA_INFO_LOG_TIME_NS,
            publish_time=CAMERA_INFO_LOG_TIME_NS,
            data=b"",
        )
        writer.finish()
    return path


def write_mcap_with_malformed_json_video(path: Path) -> Path:
    """Writes an MCAP whose video topic is JSON-encoded with malformed payloads.

    The schema name marks the topic as video, and its encoding has a decoder, but
    the payloads are not valid JSON, so no keyframe can be detected.

    Args:
        path: The path to write the file to.

    Returns:
        The path of the written file.
    """
    with path.open("wb") as stream:
        writer = RawWriter(output=stream)
        writer.start()
        schema_id = writer.register_schema(
            name="foxglove_msgs/msg/CompressedVideo", encoding="jsonschema", data=b""
        )
        channel_id = writer.register_channel(
            topic=CAMERA_VIDEO_TOPIC, message_encoding="json", schema_id=schema_id
        )
        for log_time_ns in VIDEO_LOG_TIMES_NS:
            writer.add_message(
                channel_id=channel_id,
                log_time=log_time_ns,
                publish_time=log_time_ns,
                data=b"not valid json",
            )
        writer.finish()
    return path


def h265_keyframe(payload: bytes = b"\x00\x01\x02") -> bytes:
    """Returns an Annex B H.265 frame holding an IDR picture."""
    return b"\x00\x00\x00\x01\x26\x01" + payload


def h265_delta_frame(payload: bytes = b"\x00\x01\x02") -> bytes:
    """Returns an Annex B H.265 frame holding a trailing picture."""
    return b"\x00\x00\x00\x01\x02\x01" + payload


def h264_keyframe(payload: bytes = b"\x00\x01\x02") -> bytes:
    """Returns an Annex B H.264 frame holding an IDR picture."""
    return b"\x00\x00\x00\x01\x65" + payload


def h264_delta_frame(payload: bytes = b"\x00\x01\x02") -> bytes:
    """Returns an Annex B H.264 frame holding a non-IDR picture."""
    return b"\x00\x00\x00\x01\x41" + payload


def _compressed_video_message(log_time_ns: int) -> dict[str, Any]:
    is_keyframe = log_time_ns in VIDEO_KEYFRAME_LOG_TIMES_NS
    return {
        "timestamp": _time(log_time_ns),
        "frame_id": CAMERA_FRAME_ID,
        "data": h265_keyframe() if is_keyframe else h265_delta_frame(),
        "format": "h265",
    }


def _camera_info_message() -> dict[str, Any]:
    return {
        "header": {"stamp": _time(CAMERA_INFO_LOG_TIME_NS), "frame_id": CAMERA_FRAME_ID},
        "height": IMAGE_HEIGHT,
        "width": IMAGE_WIDTH,
        "distortion_model": "plumb_bob",
        "d": [0.1, 0.01, 0.0, 0.0, 0.0],
        "k": list(CAMERA_MATRIX),
        "r": [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0],
        "p": [600.0, 0.0, 320.0, 0.0, 0.0, 600.0, 240.0, 0.0, 0.0, 0.0, 1.0, 0.0],
        "binning_x": 0,
        "binning_y": 0,
        "roi": {
            "x_offset": 0,
            "y_offset": 0,
            "height": 0,
            "width": 0,
            "do_rectify": False,
        },
    }


def _point_cloud_message() -> dict[str, Any]:
    return {
        "header": {"stamp": _time(LIDAR_LOG_TIMES_NS[0]), "frame_id": LIDAR_FRAME_ID},
        "height": 1,
        "width": 1,
        "fields": [{"name": "x", "offset": 0, "datatype": 7, "count": 1}],
        "is_bigendian": False,
        "point_step": 4,
        "row_step": 4,
        "data": b"\x00\x00\x00\x00",
        "is_dense": True,
    }


def _static_transforms_message() -> dict[str, Any]:
    """Returns a TF message with the camera and the lidar mounted on the base frame.

    The camera is rotated by 90 degrees around the z axis, so that composing the two
    edges gives a transform that is not a pure translation.
    """
    return {
        "transforms": [
            _transform_stamped(
                child_frame_id=CAMERA_FRAME_ID,
                translation=(1.0, 0.0, 2.0),
                rotation=(0.0, 0.0, 0.7071067811865476, 0.7071067811865476),
            ),
            _transform_stamped(
                child_frame_id=LIDAR_FRAME_ID,
                translation=(0.0, 1.0, 2.0),
                rotation=(0.0, 0.0, 0.0, 1.0),
            ),
        ]
    }


def _transform_stamped(
    child_frame_id: str,
    translation: tuple[float, float, float],
    rotation: tuple[float, float, float, float],
) -> dict[str, Any]:
    x, y, z = translation
    quaternion_x, quaternion_y, quaternion_z, quaternion_w = rotation
    return {
        "header": {
            "stamp": _time(STATIC_TRANSFORM_LOG_TIME_NS),
            "frame_id": BASE_FRAME_ID,
        },
        "child_frame_id": child_frame_id,
        "transform": {
            "translation": {"x": x, "y": y, "z": z},
            "rotation": {
                "x": quaternion_x,
                "y": quaternion_y,
                "z": quaternion_z,
                "w": quaternion_w,
            },
        },
    }


def _time(log_time_ns: int) -> dict[str, int]:
    return {"sec": log_time_ns // 1_000_000_000, "nanosec": log_time_ns % 1_000_000_000}
