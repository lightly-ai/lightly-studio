from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from lightly_studio.dataset.file_utils import download_file_if_does_not_exist


def _mock_response(mocker):
    """Helper to create a mock requests response."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.raw = io.BytesIO(b"test")
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    mocker.patch("lightly_studio.dataset.file_utils.requests.get", return_value=mock_resp)
    return mock_resp


def test_download_file_if_does_not_exist__success(tmp_path: Path, mocker: MockerFixture) -> None:
    target = tmp_path / "model.pt"
    _mock_response(mocker=mocker)

    download_file_if_does_not_exist(url="http://example.com/model.pt", local_filename=target)

    assert target.exists()
    assert target.read_bytes() == b"test"


def test_download_file_if_does_not_exist__sigint_cleans_up(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    target = tmp_path / "model.pt"
    _mock_response(mocker)
    # emulate SIGINT
    mocker.patch(
        "lightly_studio.dataset.file_utils.shutil.copyfileobj",
        side_effect=KeyboardInterrupt,
    )

    with pytest.raises(KeyboardInterrupt):
        download_file_if_does_not_exist(url="http://example.com/model.pt", local_filename=target)

    assert not target.exists()
    assert not list(tmp_path.glob("tmp*"))


def test_download_file_if_does_not_exist__sigterm_cleans_up(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    target = tmp_path / "model.pt"
    _mock_response(mocker)
    # emulate SIGTERM
    mocker.patch(
        "lightly_studio.dataset.file_utils.shutil.copyfileobj",
        side_effect=SystemExit,
    )

    with pytest.raises(SystemExit):
        download_file_if_does_not_exist(url="http://example.com/model.pt", local_filename=target)

    assert not target.exists()
    assert not list(tmp_path.glob("tmp*"))


def test_download_file_if_does_not_exist__network_error_cleans_up(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    target = tmp_path / "model.pt"
    _mock_response(mocker)
    mocker.patch(
        "lightly_studio.dataset.file_utils.requests.get",
        side_effect=ConnectionError("Network failed"),
    )

    with pytest.raises(ConnectionError):
        download_file_if_does_not_exist(url="http://example.com/model.pt", local_filename=target)

    assert not target.exists()
    assert not list(tmp_path.glob("tmp*"))


def test_download_file_if_does_not_exist__existing_file_skips_download(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    target = tmp_path / "model.pt"
    target.write_bytes(b"existing content")
    mock_get = mocker.patch("lightly_studio.dataset.file_utils.requests.get")

    download_file_if_does_not_exist(url="http://example.com/model.pt", local_filename=target)

    mock_get.assert_not_called()
    assert target.read_bytes() == b"existing content"


def test_download_file_if_does_not_exist__creates_parent_directory(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    target = tmp_path / "nested" / "model.pt"
    _mock_response(mocker)

    assert not target.parent.exists()
    download_file_if_does_not_exist(url="http://example.com/model.pt", local_filename=target)

    assert target.exists()
    assert target.read_bytes() == b"test"


def test_download_file_if_does_not_exist__cleanup_failure_logs_warning(
    tmp_path: Path, mocker: MockerFixture, caplog: pytest.LogCaptureFixture
) -> None:
    import logging

    target = tmp_path / "model.pt"
    _mock_response(mocker)
    mocker.patch(
        "lightly_studio.dataset.file_utils.shutil.copyfileobj",
        side_effect=ConnectionError("Network failed"),
    )
    mocker.patch(
        "lightly_studio.dataset.file_utils.os.remove",
        side_effect=OSError("Permission denied"),
    )

    with caplog.at_level(logging.WARNING), pytest.raises(ConnectionError):
        download_file_if_does_not_exist("http://fake.url/model.pt", target)

    assert "Failed to clean up temp file" in caplog.text
    assert "Permission denied" in caplog.text
