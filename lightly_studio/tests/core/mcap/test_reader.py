from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import boto3
import fsspec
import numpy as np
import pytest
from mcap.exceptions import InvalidMagic
from moto.server import ThreadedMotoServer
from pytest_mock import MockerFixture

from lightly_studio.core.mcap import matching
from lightly_studio.core.mcap import reader as reader_module
from lightly_studio.core.mcap.errors import (
    ChannelNotFoundError,
    DataNotLoadedError,
    McapAccessError,
    TopicNotFoundError,
)
from lightly_studio.core.mcap.reader import McapFileReader, ReadPattern
from tests.core.mcap import helpers

# The bucket and key the recording is uploaded to, to read it back over S3.
S3_BUCKET = "test-recordings"
S3_KEY = "recordings/recording.mcap"
S3_ACCESS_KEY = "testing"
S3_SECRET_KEY = "testing"
S3_REGION = "us-east-1"


@pytest.fixture(scope="module")
def mcap_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return helpers.write_mcap(tmp_path_factory.mktemp("mcap") / "recording.mcap")


@pytest.fixture
def reader(mcap_path: Path) -> Iterator[McapFileReader]:
    with McapFileReader(mcap_path) as mcap_file_reader:
        yield mcap_file_reader


@pytest.fixture(scope="module")
def moto_server() -> Iterator[ThreadedMotoServer]:
    """Runs a mock S3 server on a free port."""
    server = ThreadedMotoServer(ip_address="localhost", port=0)
    server.start()
    yield server
    server.stop()


@pytest.fixture(scope="module")
def s3_storage_options(moto_server: ThreadedMotoServer) -> dict[str, Any]:
    """Returns the fsspec options that point s3fs at the mock S3 server."""
    host, port = moto_server.get_host_and_port()
    return {
        "key": S3_ACCESS_KEY,
        "secret": S3_SECRET_KEY,
        "client_kwargs": {"endpoint_url": f"http://{host}:{port}", "region_name": S3_REGION},
    }


@pytest.fixture(scope="module")
def s3_mcap_uri(moto_server: ThreadedMotoServer, mcap_path: Path) -> str:
    """Uploads the recording to the mock S3 server and returns its URI."""
    host, port = moto_server.get_host_and_port()
    client = boto3.client(
        "s3",
        endpoint_url=f"http://{host}:{port}",
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        region_name=S3_REGION,
    )
    client.create_bucket(Bucket=S3_BUCKET)
    client.put_object(Bucket=S3_BUCKET, Key=S3_KEY, Body=mcap_path.read_bytes())
    return f"s3://{S3_BUCKET}/{S3_KEY}"


class TestMcapFileReader:
    def test_get_frame_locators(self, reader: McapFileReader) -> None:
        reader.load_data_for_topics([helpers.CAMERA_VIDEO_TOPIC, helpers.LIDAR_POINTS_TOPIC])

        video_locators = reader.get_frame_locators(helpers.CAMERA_VIDEO_TOPIC)
        lidar_locators = reader.get_frame_locators(helpers.LIDAR_POINTS_TOPIC)

        assert [locator.log_time_ns for locator in video_locators] == list(
            helpers.VIDEO_LOG_TIMES_NS
        )
        assert [locator.log_time_ns for locator in lidar_locators] == list(
            helpers.LIDAR_LOG_TIMES_NS
        )
        assert [locator.capture_timestamp_ns for locator in video_locators] == list(
            helpers.VIDEO_LOG_TIMES_NS
        )
        assert [locator.capture_timestamp_ns for locator in lidar_locators] == list(
            helpers.LIDAR_LOG_TIMES_NS
        )
        # Only the video topic tracks keyframes, and it does so in the combined pass.
        assert [locator.keyframe_log_time_ns for locator in video_locators] == [
            helpers.VIDEO_KEYFRAME_LOG_TIMES_NS[0],
            helpers.VIDEO_KEYFRAME_LOG_TIMES_NS[0],
            helpers.VIDEO_KEYFRAME_LOG_TIMES_NS[1],
            helpers.VIDEO_KEYFRAME_LOG_TIMES_NS[1],
        ]
        assert all(locator.keyframe_log_time_ns is None for locator in lidar_locators)

    def test_get_frame_locators__capture_timestamp_differs_from_log_time(
        self, tmp_path: Path
    ) -> None:
        path = helpers.write_mcap(tmp_path / "offset.mcap", lidar_stamp_offset_ns=-50_000_000)

        with McapFileReader(path) as reader:
            reader.load_data_for_topics([helpers.LIDAR_POINTS_TOPIC])
            locators = reader.get_frame_locators(helpers.LIDAR_POINTS_TOPIC)

        assert [locator.capture_timestamp_ns for locator in locators] == [
            helpers.LIDAR_LOG_TIMES_NS[0] - 50_000_000,
            helpers.LIDAR_LOG_TIMES_NS[1] - 50_000_000,
        ]
        assert [locator.log_time_ns for locator in locators] == list(helpers.LIDAR_LOG_TIMES_NS)

    def test_get_frame_locators__video_without_decoder(self, tmp_path: Path) -> None:
        path = helpers.write_mcap_with_undecodable_video(tmp_path / "undecodable.mcap")

        with McapFileReader(path) as reader:
            reader.load_data_for_topics([helpers.CAMERA_VIDEO_TOPIC])
            locators = reader.get_frame_locators(helpers.CAMERA_VIDEO_TOPIC)

        assert locators == []

    def test_get_frame_locators__time_range(self, reader: McapFileReader) -> None:
        reader.load_data_for_topics(
            [helpers.CAMERA_VIDEO_TOPIC, helpers.LIDAR_POINTS_TOPIC],
            start_time_ns=helpers.VIDEO_LOG_TIMES_NS[1],
            end_time_ns=helpers.VIDEO_LOG_TIMES_NS[3],
        )

        video_locators = reader.get_frame_locators(helpers.CAMERA_VIDEO_TOPIC)
        # The first lidar sweep is logged before the range, so only the second remains.
        lidar_locators = reader.get_frame_locators(helpers.LIDAR_POINTS_TOPIC)

        assert [locator.log_time_ns for locator in video_locators] == [
            helpers.VIDEO_LOG_TIMES_NS[1],
            helpers.VIDEO_LOG_TIMES_NS[2],
        ]
        assert [locator.log_time_ns for locator in lidar_locators] == [
            helpers.LIDAR_LOG_TIMES_NS[1]
        ]

    def test_get_frame_locators__malformed_video_payload(self, tmp_path: Path) -> None:
        path = helpers.write_mcap_with_malformed_json_video(tmp_path / "malformed.mcap")

        with McapFileReader(path) as reader:
            reader.load_data_for_topics([helpers.CAMERA_VIDEO_TOPIC])
            locators = reader.get_frame_locators(helpers.CAMERA_VIDEO_TOPIC)

        assert locators == []

    def test_get_frame_locators__video_without_timestamp(self, tmp_path: Path) -> None:
        path = helpers.write_mcap_with_malformed_json_video(
            tmp_path / "no_timestamp.mcap", payload=b'{"frame_id": "camera"}'
        )

        with McapFileReader(path) as reader:
            reader.load_data_for_topics([helpers.CAMERA_VIDEO_TOPIC])
            locators = reader.get_frame_locators(helpers.CAMERA_VIDEO_TOPIC)

        assert locators == []

    def test_get_frame_locators__repeated_topic(self, reader: McapFileReader) -> None:
        reader.load_data_for_topics([helpers.LIDAR_POINTS_TOPIC, helpers.LIDAR_POINTS_TOPIC])

        locators = reader.get_frame_locators(helpers.LIDAR_POINTS_TOPIC)

        assert [locator.log_time_ns for locator in locators] == list(helpers.LIDAR_LOG_TIMES_NS)

    def test_load_data_for_topics__no_topics(self, reader: McapFileReader) -> None:
        reader.load_data_for_topics([])

        with pytest.raises(DataNotLoadedError):
            reader.get_frame_locators(helpers.LIDAR_POINTS_TOPIC)

    def test_load_data_for_topics__unknown_topic(self, reader: McapFileReader) -> None:
        with pytest.raises(TopicNotFoundError):
            reader.load_data_for_topics([helpers.LIDAR_POINTS_TOPIC, "/unknown"])

    def test_get_frame_locators__not_loaded(self, reader: McapFileReader) -> None:
        with pytest.raises(DataNotLoadedError, match=helpers.LIDAR_POINTS_TOPIC):
            reader.get_frame_locators(helpers.LIDAR_POINTS_TOPIC)

    def test_get_frame_locators__sync_timestamps(self, reader: McapFileReader) -> None:
        reader.load_data_for_topics([helpers.CAMERA_VIDEO_TOPIC])

        locators = reader.get_frame_locators(
            helpers.CAMERA_VIDEO_TOPIC,
            sync_timestamps=[1_040_000_000, 1_190_000_000],
        )

        assert [locator.log_time_ns for locator in locators if locator is not None] == [
            helpers.VIDEO_LOG_TIMES_NS[0],
            helpers.VIDEO_LOG_TIMES_NS[2],
        ]

    def test_get_frame_locators__sync_timestamps_miss(self, reader: McapFileReader) -> None:
        reader.load_data_for_topics([helpers.CAMERA_VIDEO_TOPIC])

        locators = reader.get_frame_locators(
            helpers.CAMERA_VIDEO_TOPIC,
            sync_timestamps=[1_040_000_000, 9_000_000_000],
            sync_rule=matching.closest(max_diff_ns=50_000_000),
        )

        assert locators[0] is not None
        assert locators[0].log_time_ns == helpers.VIDEO_LOG_TIMES_NS[0]
        assert locators[1] is None

    def test_get_frame_locators__sync_timestamps_empty(self, reader: McapFileReader) -> None:
        reader.load_data_for_topics([helpers.CAMERA_VIDEO_TOPIC])

        assert reader.get_frame_locators(helpers.CAMERA_VIDEO_TOPIC, sync_timestamps=[]) == []

    def test_get_intrinsic(self, reader: McapFileReader) -> None:
        intrinsics = reader.get_intrinsic(topic=helpers.CAMERA_INFO_TOPIC)

        assert intrinsics.width == helpers.IMAGE_WIDTH
        assert intrinsics.height == helpers.IMAGE_HEIGHT
        assert intrinsics.camera_matrix == helpers.CAMERA_MATRIX
        assert intrinsics.frame_id == helpers.CAMERA_FRAME_ID
        assert intrinsics.distortion_model == "plumb_bob"

    def test_get_intrinsic__repeated(self, reader: McapFileReader) -> None:
        first = reader.get_intrinsic(topic=helpers.CAMERA_INFO_TOPIC)
        second = reader.get_intrinsic(topic=helpers.CAMERA_INFO_TOPIC)

        assert first == second

    def test_get_intrinsic__unknown_topic(self, reader: McapFileReader) -> None:
        with pytest.raises(TopicNotFoundError):
            reader.get_intrinsic(topic="/unknown")

    def test_get_intrinsic__not_camera_info(self, reader: McapFileReader) -> None:
        with pytest.raises(McapAccessError, match="has no field 'k', 'K'"):
            reader.get_intrinsic(topic=helpers.CAMERA_VIDEO_TOPIC)

    def test_get_intrinsic__undecodable(self, tmp_path: Path) -> None:
        path = helpers.write_mcap_with_undecodable_camera_info(tmp_path / "undecodable.mcap")

        with McapFileReader(path) as reader, pytest.raises(McapAccessError, match="Cannot decode"):
            reader.get_intrinsic(topic=helpers.CAMERA_INFO_TOPIC)

    def test_get_static_transform(self, reader: McapFileReader) -> None:
        matrix = reader.get_static_transform(
            parent_frame_id=helpers.CAMERA_FRAME_ID, child_frame_id=helpers.LIDAR_FRAME_ID
        )

        # The lidar sits 1 m to the left of the camera, which the camera sees 1 m ahead
        # and 1 m to its right because it is turned by 90 degrees.
        assert np.allclose(matrix @ [0.0, 0.0, 0.0, 1.0], [1.0, 1.0, 0.0, 1.0])

    def test_get_static_transform__repeated(self, reader: McapFileReader) -> None:
        first = reader.get_static_transform(
            parent_frame_id=helpers.CAMERA_FRAME_ID, child_frame_id=helpers.BASE_FRAME_ID
        )
        second = reader.get_static_transform(
            parent_frame_id=helpers.CAMERA_FRAME_ID, child_frame_id=helpers.BASE_FRAME_ID
        )

        assert np.allclose(first, second)

    def test_get_static_transform__unknown_topic(self, reader: McapFileReader) -> None:
        with pytest.raises(TopicNotFoundError):
            reader.get_static_transform(
                parent_frame_id=helpers.CAMERA_FRAME_ID,
                child_frame_id=helpers.LIDAR_FRAME_ID,
                topic="/unknown",
            )

    def test_get_decoded_message_at(self, tmp_path: Path) -> None:
        path = helpers.write_mcap_with_compressed_image(tmp_path / "with_image.mcap")
        with McapFileReader(path) as reader:
            channel_id = next(
                topic.channel_id
                for topic in reader.get_topics()
                if topic.name == helpers.CAMERA_IMAGE_TOPIC
            )

            result = reader.get_decoded_message_at(
                channel_id=channel_id, timestamp_ns=helpers.IMAGE_LOG_TIMES_NS[1]
            )

        assert result is not None
        assert result.channel_id == channel_id
        assert result.topic == helpers.CAMERA_IMAGE_TOPIC
        assert result.log_time_ns == helpers.IMAGE_LOG_TIMES_NS[1]
        assert result.decoded_message.data == helpers.compressed_image_payload(
            helpers.IMAGE_LOG_TIMES_NS[1]
        )

    def test_get_decoded_message_at__no_message_at_timestamp(self, tmp_path: Path) -> None:
        path = helpers.write_mcap_with_compressed_image(tmp_path / "with_image.mcap")
        with McapFileReader(path) as reader:
            channel_id = next(
                topic.channel_id
                for topic in reader.get_topics()
                if topic.name == helpers.CAMERA_IMAGE_TOPIC
            )

            result = reader.get_decoded_message_at(
                channel_id=channel_id,
                timestamp_ns=helpers.IMAGE_LOG_TIMES_NS[0] + 1,
            )

        assert result is None

    def test_get_decoded_message_at__unknown_channel(self, reader: McapFileReader) -> None:
        with pytest.raises(ChannelNotFoundError):
            reader.get_decoded_message_at(channel_id=999_999, timestamp_ns=0)

    def test_get_decoded_message_at__undecodable(self, tmp_path: Path) -> None:
        path = helpers.write_mcap_with_undecodable_compressed_image(tmp_path / "undecodable.mcap")
        with McapFileReader(path) as reader:
            channel_id = next(
                topic.channel_id
                for topic in reader.get_topics()
                if topic.name == helpers.CAMERA_IMAGE_TOPIC
            )

            with pytest.raises(McapAccessError):
                reader.get_decoded_message_at(
                    channel_id=channel_id,
                    timestamp_ns=helpers.IMAGE_LOG_TIMES_NS[0],
                )

    def test_close(self, mcap_path: Path) -> None:
        mcap_file_reader = McapFileReader(mcap_path)
        mcap_file_reader.close()

        with pytest.raises(ValueError, match="closed file"):
            mcap_file_reader.load_data_for_topics([helpers.LIDAR_POINTS_TOPIC])


def test_mcap_file_reader__unchunked(tmp_path: Path) -> None:
    path = helpers.write_unchunked_mcap(tmp_path / "unchunked.mcap")

    with McapFileReader(path) as reader, pytest.raises(McapAccessError, match="no chunk index"):
        reader.load_data_for_topics([helpers.LIDAR_POINTS_TOPIC])


def test_mcap_file_reader__not_an_mcap_file(tmp_path: Path) -> None:
    path = tmp_path / "not_an_mcap.mcap"
    path.write_bytes(b"not an mcap file")

    with pytest.raises(InvalidMagic):
        McapFileReader(path)


def test_mcap_file_reader__file_uri(mcap_path: Path) -> None:
    with McapFileReader(f"file://{mcap_path.as_posix()}") as reader:
        reader.load_data_for_topics([helpers.CAMERA_VIDEO_TOPIC])
        locators = reader.get_frame_locators(helpers.CAMERA_VIDEO_TOPIC)

    assert [locator.log_time_ns for locator in locators] == list(helpers.VIDEO_LOG_TIMES_NS)


def test_mcap_file_reader__memory_uri(mcap_path: Path) -> None:
    uri = "memory://recording.mcap"
    with fsspec.open(uri, mode="wb") as file:
        file.write(mcap_path.read_bytes())

    with McapFileReader(uri) as reader:
        reader.load_data_for_topics([helpers.CAMERA_VIDEO_TOPIC])
        locators = reader.get_frame_locators(helpers.CAMERA_VIDEO_TOPIC)

    assert [locator.log_time_ns for locator in locators] == list(helpers.VIDEO_LOG_TIMES_NS)


def test_mcap_file_reader__s3_uri(s3_mcap_uri: str, s3_storage_options: dict[str, Any]) -> None:
    with McapFileReader(s3_mcap_uri, storage_options=s3_storage_options) as reader:
        reader.load_data_for_topics([helpers.CAMERA_VIDEO_TOPIC])
        locators = reader.get_frame_locators(helpers.CAMERA_VIDEO_TOPIC)
        intrinsics = reader.get_intrinsic(topic=helpers.CAMERA_INFO_TOPIC)

    # The payloads are read over S3 too, so the keyframes are detected as locally.
    assert [locator.log_time_ns for locator in locators] == list(helpers.VIDEO_LOG_TIMES_NS)
    assert [locator.keyframe_log_time_ns for locator in locators] == [
        helpers.VIDEO_KEYFRAME_LOG_TIMES_NS[0],
        helpers.VIDEO_KEYFRAME_LOG_TIMES_NS[0],
        helpers.VIDEO_KEYFRAME_LOG_TIMES_NS[1],
        helpers.VIDEO_KEYFRAME_LOG_TIMES_NS[1],
    ]
    assert intrinsics.width == helpers.IMAGE_WIDTH
    assert intrinsics.camera_matrix == helpers.CAMERA_MATRIX


def test_mcap_file_reader__s3_uri_cached(
    s3_mcap_uri: str, s3_storage_options: dict[str, Any], tmp_path: Path
) -> None:
    """A chained caching URI keeps the fetched bytes on local disk."""
    cache_path = tmp_path / "cache"
    with McapFileReader(
        f"simplecache::{s3_mcap_uri}",
        storage_options={
            "s3": s3_storage_options,
            "simplecache": {"cache_storage": str(cache_path)},
        },
    ) as reader:
        reader.load_data_for_topics([helpers.CAMERA_VIDEO_TOPIC])
        locators = reader.get_frame_locators(helpers.CAMERA_VIDEO_TOPIC)

    assert [locator.log_time_ns for locator in locators] == list(helpers.VIDEO_LOG_TIMES_NS)
    assert any(path.is_file() for path in cache_path.iterdir())


def test_mcap_file_reader__not_seekable(mocker: MockerFixture) -> None:
    stream = mocker.MagicMock()
    stream.seekable.return_value = False
    filesystem = mocker.MagicMock()
    filesystem.open.return_value = stream
    mocker.patch.object(fsspec, "url_to_fs", return_value=(filesystem, "recording.mcap"))

    with pytest.raises(McapAccessError, match="random access"):
        McapFileReader("https://example.com/recording.mcap")

    stream.close.assert_called_once_with()


def test_mcap_file_reader__read_pattern_random(mcap_path: Path) -> None:
    with McapFileReader(mcap_path, read_pattern=ReadPattern.RANDOM) as reader:
        reader.load_data_for_topics([helpers.CAMERA_VIDEO_TOPIC])
        locators = reader.get_frame_locators(helpers.CAMERA_VIDEO_TOPIC)

    assert [locator.log_time_ns for locator in locators] == list(helpers.VIDEO_LOG_TIMES_NS)


def test_read_cache_options() -> None:
    assert reader_module._read_cache_options(ReadPattern.SEQUENTIAL) == {}


def test_read_cache_options__random() -> None:
    options = reader_module._read_cache_options(ReadPattern.RANDOM)

    assert options["cache_type"] == "readahead"
    assert 0 < options["block_size"] <= 4 * 1024 * 1024
