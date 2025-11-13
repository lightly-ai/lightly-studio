import io
import zipfile
from pathlib import Path

import pytest
import requests
from pytest_mock import MockerFixture

from lightly_studio.utils.download import download_example_dataset


def test_download_dataset_success(mocker: MockerFixture, tmp_path: Path) -> None:
    """Tests that the function successfully downloads and extracts a mock zip file."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(file=zip_buffer, mode="w") as zf:
        zf.writestr("dataset_examples-main/test_file.txt", "hello")

    zip_buffer.seek(0)

    mock_response = mocker.MagicMock(spec=requests.Response)
    mock_response.raise_for_status.return_value = None
    mock_response.headers = {"content-length": str(len(zip_buffer.getvalue()))}
    mock_response.iter_content.return_value = [zip_buffer.getvalue()]

    mock_response.__enter__.return_value = mock_response
    mock_response.__exit__.return_value = None

    mocker.patch(target="requests.get", return_value=mock_response)

    target_dir = tmp_path / "my_data"
    download_example_dataset(target_dir=str(target_dir))

    assert target_dir.exists()
    assert (target_dir / "test_file.txt").exists()
    assert (target_dir / "test_file.txt").read_text() == "hello"

    assert not (tmp_path / "my_data.zip").exists()


def test_download_skips_if_exists(mocker: MockerFixture, tmp_path: Path) -> None:
    """Tests that the function skips downloading if the target directory exists."""
    mock_get = mocker.patch(target="requests.get")

    target_dir = tmp_path / "my_data"
    target_dir.mkdir()

    download_example_dataset(target_dir=str(target_dir), force=False)

    mock_get.assert_not_called()


def test_download_force_overwrite(mocker: MockerFixture, tmp_path: Path) -> None:
    """Tests that the function re-downloads if force=True."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(file=zip_buffer, mode="w") as zf:
        zf.writestr("dataset_examples-main/new_file.txt", "new")
    zip_buffer.seek(0)

    mock_response = mocker.MagicMock(spec=requests.Response)
    mock_response.raise_for_status.return_value = None
    mock_response.headers = {"content-length": str(len(zip_buffer.getvalue()))}
    mock_response.iter_content.return_value = [zip_buffer.getvalue()]
    mock_response.__enter__.return_value = mock_response
    mock_response.__exit__.return_value = None

    mock_get = mocker.patch(target="requests.get", return_value=mock_response)

    target_dir = tmp_path / "my_data"
    target_dir.mkdir()
    (target_dir / "old_file.txt").write_text("old")

    download_example_dataset(target_dir=str(target_dir), force=True)

    mock_get.assert_called_once()
    assert (target_dir / "new_file.txt").exists()
    assert not (target_dir / "old_file.txt").exists()


def test_download_cleanup_on_error(mocker: MockerFixture, tmp_path: Path) -> None:
    """Tests that temporary files are cleaned up if the download fails."""
    # Simulate the internet crashing
    mocker.patch(target="requests.get", side_effect=requests.RequestException("Boom"))

    target_dir = tmp_path / "data_fail"

    # Verify that the exception bubbles up to the user
    with pytest.raises(requests.RequestException, match="Boom"):
        download_example_dataset(target_dir=str(target_dir))

    # Verify the 'finally' block in download.py worked:
    # The target directory shouldn't be half-created
    assert not target_dir.exists()
    # The zip file should be gone
    assert not (tmp_path / "data_fail.zip").exists()
    # The extract folder should be gone
    assert not (tmp_path / "data_fail_temp_extract").exists()
