"""Tests for DatasetLoader.start_gui() validation."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image
from pytest_mock import MockerFixture

from lightly_studio.dataset import loader as loader_module
from lightly_studio.dataset.loader import DatasetLoader
from lightly_studio.models.dataset import DatasetCreate
from lightly_studio.resolvers import dataset_resolver


def test_start_gui__with_samples(
    mocker: MockerFixture,
    patch_loader: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    """Test that start_gui works normally when samples exist."""
    image_path = tmp_path / "sample.jpg"
    Image.new("RGB", (10, 10)).save(image_path)

    # Load the dataset
    loader = DatasetLoader()
    loader.from_directory(
        dataset_name="test_dataset",
        img_dir=str(tmp_path),
    )

    # Mock the server to avoid actually starting it
    # We must patch it in the loader module where Server was imported directly
    mock_server = mocker.patch.object(loader_module, "Server")
    mock_server_instance = mock_server.return_value

    # This should not raise an error
    loader.start_gui()

    # Verify that the server was created and started
    mock_server.assert_called_once()
    mock_server_instance.start.assert_called_once()


def test_start_gui__no_datasets(
    patch_loader: None,  # noqa: ARG001
) -> None:
    """Test that start_gui raises an error when no datasets exist."""
    loader = DatasetLoader()

    with pytest.raises(ValueError, match="No datasets found"):
        loader.start_gui()


def test_start_gui__empty_datasets(
    patch_loader: None,  # noqa: ARG001
) -> None:
    """Test that start_gui raises an error when datasets exist but contain no images."""
    loader = DatasetLoader()

    dataset_resolver.create(
        session=loader.session,
        dataset=DatasetCreate(name="empty_dataset"),
    )

    with pytest.raises(ValueError, match="No images have been indexed"):
        loader.start_gui()
