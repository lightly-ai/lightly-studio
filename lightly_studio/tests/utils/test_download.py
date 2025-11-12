import io
import zipfile
from pathlib import Path

import requests
from pytest_mock import MockerFixture

from lightly_studio.utils.download import download_example_dataset


def test_download_dataset_success(mocker: MockerFixture, tmp_path: Path) -> None:
    """Tests that the function successfully downloads and extracts a mock zip file."""
    # Create a fake zip file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        # The folder GitHub creates
        zf.writestr("dataset_examples-main/test_file.txt", "hello")

    zip_buffer.seek(0)

    # Create a mock response object for requests.get
    mock_response = mocker.MagicMock(spec=requests.Response)
    mock_response.raise_for_status.return_value = None
    mock_response.headers = {"content-length": str(len(zip_buffer.getvalue()))}

    # Make iter_content return our fake zip data
    mock_response.iter_content.return_value = [zip_buffer.getvalue()]

    # Patch requests.get to return our mock response
    mocker.patch("requests.get", return_value=mock_response)

    # Run the function (in the temp directory)
    target_dir = tmp_path / "my_data"
    download_example_dataset(target_dir=str(target_dir))

    # Assert the files were created correctly
    assert target_dir.exists()
    assert (target_dir / "test_file.txt").exists()
    assert (target_dir / "test_file.txt").read_text() == "hello"

    # Assert the temporary zip file was cleaned up
    assert not (tmp_path / "my_data.zip").exists()


def test_download_skips_if_exists(mocker: MockerFixture, tmp_path: Path) -> None:
    """Tests that the function skips downloading if the target directory exists."""
    # Patch requests.get so we can check if it was called
    mock_get = mocker.patch("requests.get")

    # Create the target directory beforehand
    target_dir = tmp_path / "my_data"
    target_dir.mkdir()

    # Run the function
    download_example_dataset(target_dir=str(target_dir), force=False)

    # Assert that requests.get was NOT called
    mock_get.assert_not_called()


def test_download_force_overwrite(mocker: MockerFixture, tmp_path: Path) -> None:
    """Tests that the function re-downloads if force=True."""
    # Set up the same mocks as the first test (test_download_dataset_success)
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("dataset_examples-main/new_file.txt", "new")
    zip_buffer.seek(0)

    mock_response = mocker.MagicMock(spec=requests.Response)
    mock_response.raise_for_status.return_value = None
    mock_response.headers = {"content-length": str(len(zip_buffer.getvalue()))}
    mock_response.iter_content.return_value = [zip_buffer.getvalue()]

    mock_get = mocker.patch("requests.get", return_value=mock_response)

    # Create the target directory beforehand
    target_dir = tmp_path / "my_data"
    target_dir.mkdir()
    (target_dir / "old_file.txt").write_text("old")

    # Run the function with force=True
    download_example_dataset(target_dir=str(target_dir), force=True)

    # Assert that requests.get WAS called
    mock_get.assert_called_once()

    # Assert the new file is there and the old one is gone
    assert (target_dir / "new_file.txt").exists()
    assert not (target_dir / "old_file.txt").exists()
