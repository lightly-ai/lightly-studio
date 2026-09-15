from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import boto3
import fsspec
import pytest
from mcap.exceptions import InvalidMagic
from moto.server import ThreadedMotoServer
from pytest_mock import MockerFixture

from lightly_studio.core.mcap import matching
from lightly_studio.core.mcap.errors import DataNotLoadedError, McapAccessError, TopicNotFoundError
from lightly_studio.core.mcap.reader import McapFileReader
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
        reader.load_data_for_topics([helpers.LIDAR_POINTS_TOPIC])

        locators = reader.get_frame_locators(helpers.LIDAR_POINTS_TOPIC)

        assert [locator.log_time_ns for locator in locators] == list(helpers.LIDAR_LOG_TIMES_NS)
        assert all(locator.keyframe_log_time_ns is None for locator in locators)

    def test_get_frame_locators__time_range(self, reader: McapFileReader) -> None:
        reader.load_data_for_topics(
            [helpers.LIDAR_POINTS_TOPIC],
            start_time_ns=helpers.LIDAR_LOG_TIMES_NS[0] + 1,
            end_time_ns=helpers.LIDAR_LOG_TIMES_NS[1] + 1,
        )

        locators = reader.get_frame_locators(helpers.LIDAR_POINTS_TOPIC)

        assert [locator.log_time_ns for locator in locators] == [helpers.LIDAR_LOG_TIMES_NS[1]]

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
        reader.load_data_for_topics([helpers.LIDAR_POINTS_TOPIC])

        locators = reader.get_frame_locators(
            helpers.LIDAR_POINTS_TOPIC,
            sync_timestamps=[1_040_000_000, 1_240_000_000],
        )

        assert [locator.log_time_ns for locator in locators if locator is not None] == [
            helpers.LIDAR_LOG_TIMES_NS[0],
            helpers.LIDAR_LOG_TIMES_NS[1],
        ]

    def test_get_frame_locators__sync_timestamps_miss(self, reader: McapFileReader) -> None:
        reader.load_data_for_topics([helpers.LIDAR_POINTS_TOPIC])

        locators = reader.get_frame_locators(
            helpers.LIDAR_POINTS_TOPIC,
            sync_timestamps=[1_040_000_000, 9_000_000_000],
            sync_rule=matching.closest(max_diff_ns=50_000_000),
        )

        assert locators[0] is not None
        assert locators[0].log_time_ns == helpers.LIDAR_LOG_TIMES_NS[0]
        assert locators[1] is None

    def test_get_frame_locators__sync_timestamps_empty(self, reader: McapFileReader) -> None:
        reader.load_data_for_topics([helpers.LIDAR_POINTS_TOPIC])

        assert reader.get_frame_locators(helpers.LIDAR_POINTS_TOPIC, sync_timestamps=[]) == []

    def test_close(self, mcap_path: Path) -> None:
        mcap_file_reader = McapFileReader(mcap_path)
        mcap_file_reader.close()

        with pytest.raises(ValueError, match="closed file"):
            mcap_file_reader.load_data_for_topics([helpers.LIDAR_POINTS_TOPIC])


def test_mcap_file_reader__not_an_mcap_file(tmp_path: Path) -> None:
    path = tmp_path / "not_an_mcap.mcap"
    path.write_bytes(b"not an mcap file")

    with pytest.raises(InvalidMagic):
        McapFileReader(path)


def test_mcap_file_reader__file_uri(mcap_path: Path) -> None:
    with McapFileReader(f"file://{mcap_path.as_posix()}") as reader:
        reader.load_data_for_topics([helpers.LIDAR_POINTS_TOPIC])
        locators = reader.get_frame_locators(helpers.LIDAR_POINTS_TOPIC)

    assert [locator.log_time_ns for locator in locators] == list(helpers.LIDAR_LOG_TIMES_NS)


def test_mcap_file_reader__memory_uri(mcap_path: Path) -> None:
    uri = "memory://recording.mcap"
    with fsspec.open(uri, mode="wb") as file:
        file.write(mcap_path.read_bytes())

    with McapFileReader(uri) as reader:
        reader.load_data_for_topics([helpers.LIDAR_POINTS_TOPIC])
        locators = reader.get_frame_locators(helpers.LIDAR_POINTS_TOPIC)

    assert [locator.log_time_ns for locator in locators] == list(helpers.LIDAR_LOG_TIMES_NS)


def test_mcap_file_reader__s3_uri(s3_mcap_uri: str, s3_storage_options: dict[str, Any]) -> None:
    with McapFileReader(s3_mcap_uri, storage_options=s3_storage_options) as reader:
        reader.load_data_for_topics([helpers.LIDAR_POINTS_TOPIC])
        locators = reader.get_frame_locators(helpers.LIDAR_POINTS_TOPIC)

    assert [locator.log_time_ns for locator in locators] == list(helpers.LIDAR_LOG_TIMES_NS)


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
        reader.load_data_for_topics([helpers.LIDAR_POINTS_TOPIC])
        locators = reader.get_frame_locators(helpers.LIDAR_POINTS_TOPIC)

    assert [locator.log_time_ns for locator in locators] == list(helpers.LIDAR_LOG_TIMES_NS)
    assert any(path.is_file() for path in cache_path.iterdir())


def test_mcap_file_reader__not_seekable(mocker: MockerFixture) -> None:
    stream = mocker.MagicMock()
    stream.seekable.return_value = False
    open_file = mocker.MagicMock()
    open_file.open.return_value = stream
    mocker.patch.object(fsspec, "open", return_value=open_file)

    with pytest.raises(McapAccessError, match="random access"):
        McapFileReader("https://example.com/recording.mcap")

    open_file.close.assert_called_once_with()
