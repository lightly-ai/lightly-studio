"""Tests for start_gui() validation."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image
from pytest_mock import MockerFixture

from lightly_studio import Dataset, db_manager
from lightly_studio.core import start_gui as start_gui_module
from lightly_studio.core.start_gui import start_gui
from lightly_studio.dataset import env as dataset_env
from lightly_studio.models.dataset import DatasetCreate
from lightly_studio.models.sample_type import SampleType
from lightly_studio.resolvers import dataset_resolver


def test_start_gui__with_samples(
    mocker: MockerFixture,
    patch_dataset: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    """Test that start_gui works normally when samples exist."""
    image_path = tmp_path / "sample.jpg"
    Image.new("RGB", (10, 10)).save(image_path)

    # Load the dataset using the new Dataset interface
    dataset = Dataset.create("test_dataset")
    dataset.add_samples_from_path(path=tmp_path)

    # Mock the server to avoid actually starting it
    # We must patch it in the start_gui module where Server was imported directly
    mock_server = mocker.patch.object(start_gui_module, "Server")
    mock_server_instance = mock_server.return_value

    # This should not raise an error
    start_gui()

    # Verify that the server was created with expected args and started
    mock_server.assert_called_once_with(
        host=dataset_env.LIGHTLY_STUDIO_HOST,
        port=dataset_env.LIGHTLY_STUDIO_PORT,
    )
    mock_server_instance.start.assert_called_once_with()


def test_start_gui__no_datasets(
    patch_dataset: None,  # noqa: ARG001
) -> None:
    """Test that start_gui raises an error when no datasets exist."""
    with pytest.raises(ValueError, match="No datasets found"):
        start_gui()


def test_start_gui__empty_datasets(
    patch_dataset: None,  # noqa: ARG001
) -> None:
    """Test that start_gui raises an error when datasets exist but contain no images."""
    # We can't easily create a dataset with no samples using the Dataset class
    # because it validates the path, so we'll create one through the resolver
    # Note: This bypasses the Dataset class's normal creation flow
    session = db_manager.persistent_session()

    dataset_resolver.create(
        session=session,
        dataset=DatasetCreate(name="empty_dataset_direct", sample_type=SampleType.IMAGE),
    )

    with pytest.raises(ValueError, match="No images have been indexed"):
        start_gui()
