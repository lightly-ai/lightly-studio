"""Tests for encode_point_cloud_message."""

from __future__ import annotations

import io
import struct

import numpy as np
from pyarrow import ipc
from pytest_mock import MockerFixture

from lightly_studio.core.mcap.reader import McapFileReader
from lightly_studio.core.mcap.type_definitions import DecodedMessage, StaticTransform
from lightly_studio.services.recording_service import (
    encode_point_cloud_message,
    transform_to_target_frame,
)
from lightly_studio.services.recording_service.load_dynamic_transforms import (
    DynamicTransformsByTime,
)

_FLOAT32_DATATYPE = 7
# The capture time of the message is 2 s. Its log time is 2.5 s.
CAPTURE_TIME_NS = 2_000_000_000
LOG_TIME_NS = 2_500_000_000


def test_encode_point_cloud_message__in_sensor_frame(mocker: MockerFixture) -> None:
    transform = mocker.spy(transform_to_target_frame, "transform_to_target_frame")

    data = encode_point_cloud_message.encode_point_cloud_message(
        reader=mocker.MagicMock(spec=McapFileReader),
        message=_message(),
        target_frame_id="lidar",
        static_transforms=[],
        dynamic_transforms=None,
    )

    assert _x_values(data=data) == [1.0]
    transform.assert_not_called()


def test_encode_point_cloud_message__uses_dynamic_transforms_near_capture_time(
    mocker: MockerFixture,
) -> None:
    translation = np.eye(4)
    translation[0, 3] = 10.0
    transform = mocker.patch.object(
        transform_to_target_frame, "transform_to_target_frame", return_value=translation
    )
    near_edge = _edge(timestamp_ns=CAPTURE_TIME_NS)

    data = encode_point_cloud_message.encode_point_cloud_message(
        reader=mocker.MagicMock(spec=McapFileReader),
        message=_message(),
        target_frame_id="map",
        static_transforms=[],
        dynamic_transforms=DynamicTransformsByTime(
            edges=[near_edge, _edge(timestamp_ns=LOG_TIME_NS)]
        ),
    )

    assert _x_values(data=data) == [11.0]
    assert transform.call_args.kwargs["timestamp_ns"] == CAPTURE_TIME_NS
    assert transform.call_args.kwargs["dynamic_transforms"] == [near_edge]


def test_encode_point_cloud_message__reads_dynamic_transforms_from_the_file(
    mocker: MockerFixture,
) -> None:
    transform = mocker.patch.object(
        transform_to_target_frame, "transform_to_target_frame", return_value=np.eye(4)
    )

    encode_point_cloud_message.encode_point_cloud_message(
        reader=mocker.MagicMock(spec=McapFileReader),
        message=_message(),
        target_frame_id="map",
        static_transforms=[],
        dynamic_transforms=None,
    )

    assert transform.call_args.kwargs["dynamic_transforms"] is None


def test_transform_timestamp_ns() -> None:
    assert encode_point_cloud_message.transform_timestamp_ns(message=_message()) == (
        CAPTURE_TIME_NS
    )


def _message() -> DecodedMessage:
    """Returns a one-point cloud at (1, 2, 3) in the `lidar` frame."""
    return DecodedMessage(
        channel_id=1,
        topic="/points",
        log_time_ns=LOG_TIME_NS,
        schema_name="sensor_msgs/msg/PointCloud2",
        decoded_message={
            "header": {"frame_id": "lidar", "stamp": {"sec": 2, "nanosec": 0}},
            "width": 1,
            "height": 1,
            "point_step": 12,
            "row_step": 12,
            "data": struct.pack("<fff", 1.0, 2.0, 3.0),
            "fields": [
                {"name": name, "datatype": _FLOAT32_DATATYPE, "count": 1, "offset": index * 4}
                for index, name in enumerate(("x", "y", "z"))
            ],
            "is_bigendian": False,
        },
    )


def _edge(timestamp_ns: int) -> StaticTransform:
    """Returns a `map` to `base_link` edge at a capture time."""
    return StaticTransform(
        parent_frame_id="map",
        child_frame_id="base_link",
        translation=(0.0, 0.0, 0.0),
        rotation=(0.0, 0.0, 0.0, 1.0),
        timestamp_ns=timestamp_ns,
    )


def _x_values(data: bytes) -> list[float]:
    with ipc.open_stream(io.BytesIO(data)) as stream:
        return list(stream.read_all().column("x").to_pylist())
