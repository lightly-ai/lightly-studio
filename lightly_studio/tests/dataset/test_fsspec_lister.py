from __future__ import annotations

import os
from typing import Any, Generator

import boto3
import fsspec
import pytest
import s3fs  # type: ignore[import-untyped]
from moto.server import ThreadedMotoServer
from pytest_mock import MockerFixture

from lightly_studio.dataset import fsspec_lister


@pytest.fixture(scope="session")
def moto_server() -> Generator[ThreadedMotoServer, None, None]:
    """Start a moto server for S3 testing on a free port."""
    server = ThreadedMotoServer(ip_address="localhost", port=0)
    server.start()
    yield server
    server.stop()


@pytest.fixture
def s3_bucket(moto_server: ThreadedMotoServer) -> str:
    """Create a mock S3 bucket with test data using moto server."""
    host, port = moto_server.get_host_and_port()
    endpoint = f"http://{host}:{port}"
    # Set environment variables to use moto's mock endpoints
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

    # Create S3 client pointing to moto server
    s3_client = boto3.client("s3", region_name="us-east-1", endpoint_url=endpoint)

    # Create bucket
    bucket_name = "test"
    s3_client.create_bucket(Bucket=bucket_name)

    # Upload test files to simulate the structure:
    # images/
    # ├── image1.bmp
    # ├── image2.png
    # ├── image3.jpg
    # ├── image4.jpg
    # ├── subdir/
    # │   └── image5.jpg
    # ├── text.txt
    # └── empty_dir/

    test_files = {
        "images/image1.bmp": b"fake_bmp_content",
        "images/image2.png": b"fake_png_content",
        "images/image3.jpg": b"fake_jpg_content",
        "images/image4.jpg": b"fake_jpg_content",
        "images/subdir/image5.jpg": b"fake_jpg_content",
        "images/text.txt": b"fake_text_content",
    }

    for key, content in test_files.items():
        s3_client.put_object(Bucket=bucket_name, Key=key, Body=content)

    # Create empty directory marker
    s3_client.put_object(Bucket=bucket_name, Key="images/empty_dir/")

    return bucket_name


@pytest.fixture
def mock_fsspec_s3fs(moto_server: ThreadedMotoServer) -> Generator[None, None, None]:
    """Mock fsspec to use moto server endpoint."""
    host, port = moto_server.get_host_and_port()
    endpoint = f"http://{host}:{port}"
    # Store original functions
    original_get_filesystem = fsspec_lister._get_filesystem
    original_fsspec_open = fsspec.open

    def mock_get_filesystem(path: str) -> Any:
        """Get filesystem that points to moto server."""
        if path.startswith("s3://"):
            # Configure s3fs to use moto server
            return s3fs.S3FileSystem(
                client_kwargs={"endpoint_url": endpoint},
                key="testing",
                secret="testing",
                token="testing",
            )
        return original_get_filesystem(path)

    def mock_fsspec_open(path: str, mode: str = "rb", **kwargs: Any) -> Any:
        """Mock fsspec.open to use moto server for S3 paths."""
        if path.startswith("s3://"):
            # Use the mocked filesystem for S3 paths
            fs = mock_get_filesystem(path)
            return fs.open(path, mode=mode, **kwargs)
        return original_fsspec_open(path, mode=mode, **kwargs)

    # Patch the functions
    fsspec_lister._get_filesystem = mock_get_filesystem
    fsspec.open = mock_fsspec_open

    yield

    # Restore original functions
    fsspec_lister._get_filesystem = original_get_filesystem
    fsspec.open = original_fsspec_open


class TestFsspecLister:
    """Test fsspec lister functionality."""

    def test_cloud_protocol_glob_patterns(self, mocker: MockerFixture) -> None:
        """Test S3 glob pattern matching."""
        mock_fs = mocker.MagicMock()
        mock_fs.protocol = "s3"
        mock_fs.glob.return_value = [
            "bucket/images/image1.jpg",
            "bucket/images/image2.png",
        ]
        mocker.patch.object(fsspec_lister, "_get_filesystem", return_value=mock_fs)

        result = list(fsspec_lister.iter_files_from_path("s3://bucket/images/*.*"))
        assert len(result) == 2
        assert "s3://bucket/images/image1.jpg" in result
        assert "s3://bucket/images/image2.png" in result

    def test_cloud_protocol_error_handling(self, mocker: MockerFixture) -> None:
        """Test error handling."""
        mock_fs = mocker.MagicMock()
        mock_fs.protocol = "s3"
        mock_fs.glob.side_effect = Exception("S3 connection failed")

        mocker.patch.object(fsspec_lister, "_get_filesystem", return_value=mock_fs)

        with pytest.raises(Exception, match="S3 connection failed"):
            list(fsspec_lister.iter_files_from_path("s3://bucket/images/*.jpg"))

    def test_cloud_protocol_walk_functionality(self, mocker: MockerFixture) -> None:
        """Test cloud protocol walk functionality."""
        mock_fs = mocker.MagicMock()
        mock_fs.protocol = "s3"
        mock_fs.walk.return_value = [("s3://bucket/images", [], ["image1.jpg", "image2.png"])]
        mock_fs.isfile.return_value = False
        mock_fs.isdir.return_value = True

        mocker.patch.object(fsspec_lister, "_get_filesystem", return_value=mock_fs)
        result = list(fsspec_lister.iter_files_from_path("s3://bucket/images"))
        assert len(result) == 2
        assert "s3://bucket/images/image1.jpg" in result
        assert "s3://bucket/images/image2.png" in result

    # The following tests use a mock S3 bucket created with moto
    # These tests validate the behaviour of `iter_files_from_path` for various S3 scenarios.

    def test_get_file_list_from_s3(self, s3_bucket: str, mock_fsspec_s3fs: None) -> None:  # noqa: ARG002
        result = list(fsspec_lister.iter_files_from_path("s3://test/images/"))
        assert len(result) == 5
        assert sorted(result) == [
            "s3://test/images/image1.bmp",
            "s3://test/images/image2.png",
            "s3://test/images/image3.jpg",
            "s3://test/images/image4.jpg",
            "s3://test/images/subdir/image5.jpg",
        ]

    def test_get_file_list_from_s3__single_image(
        self,
        s3_bucket: str,  # noqa: ARG002
        mock_fsspec_s3fs: None,  # noqa: ARG002
    ) -> None:
        result = list(fsspec_lister.iter_files_from_path("s3://test/images/image1.bmp"))
        assert len(result) == 1
        assert "s3://test/images/image1.bmp" in result

    def test_get_file_list_from_s3__glob(self, s3_bucket: str, mock_fsspec_s3fs: None) -> None:  # noqa: ARG002
        result = list(fsspec_lister.iter_files_from_path("s3://test/images/*.jpg"))
        assert len(result) == 2
        assert sorted(result) == ["s3://test/images/image3.jpg", "s3://test/images/image4.jpg"]

    def test_get_file_list_from_s3__glob_recursive(
        self,
        s3_bucket: str,  # noqa: ARG002
        mock_fsspec_s3fs: None,  # noqa: ARG002
    ) -> None:
        result = list(fsspec_lister.iter_files_from_path("s3://test/images/**/*.jpg"))
        assert len(result) == 3
        assert sorted(result) == [
            "s3://test/images/image3.jpg",
            "s3://test/images/image4.jpg",
            "s3://test/images/subdir/image5.jpg",
        ]

    def test_get_file_list_from_s3__allowed_extensions(
        self,
        s3_bucket: str,  # noqa: ARG002
        mock_fsspec_s3fs: None,  # noqa: ARG002
    ) -> None:
        result = list(
            fsspec_lister.iter_files_from_path(
                "s3://test/images/", allowed_extensions={".png", ".bmp"}
            )
        )
        assert len(result) == 2
        assert sorted(result) == ["s3://test/images/image1.bmp", "s3://test/images/image2.png"]

    def test_get_file_list_from_s3__invalid_path(
        self,
        s3_bucket: str,  # noqa: ARG002
        mock_fsspec_s3fs: None,  # noqa: ARG002
    ) -> None:
        with pytest.raises(Exception, match=r"Path does not exist:.*images2"):
            list(fsspec_lister.iter_files_from_path("s3://test/images2/"))

    def test_get_file_list_from_s3__text_file(self, s3_bucket: str, mock_fsspec_s3fs: None) -> None:  # noqa: ARG002
        with pytest.raises(Exception, match=r"File is not an image:.*text.txt"):
            list(fsspec_lister.iter_files_from_path("s3://test/images/text.txt"))

    def test_get_file_list_from_s3__empty_dir(self, s3_bucket: str, mock_fsspec_s3fs: None) -> None:  # noqa: ARG002
        result = list(fsspec_lister.iter_files_from_path("s3://test/images/empty_dir"))
        assert len(result) == 0

    def test_get_file_list_from_s3__single_file_read(
        self,
        s3_bucket: str,  # noqa: ARG002
        mock_fsspec_s3fs: None,  # noqa: ARG002
    ) -> None:
        result = list(fsspec_lister.iter_files_from_path("s3://test/images/image1.bmp"))
        assert len(result) == 1
        assert "s3://test/images/image1.bmp" in result
        with fsspec.open(result[0], "rb") as file:
            content = file.read()
            assert content == b"fake_bmp_content"
