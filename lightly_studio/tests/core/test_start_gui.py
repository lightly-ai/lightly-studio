"""Tests for start_gui() validation."""

from __future__ import annotations

import threading
from collections.abc import Generator
from pathlib import Path

import pytest
from PIL import Image
from pytest_mock import MockerFixture

from lightly_studio import ImageDataset, db_manager
from lightly_studio.api.server import Server
from lightly_studio.core import start_gui as start_gui_module
from lightly_studio.core.start_gui import start_gui
from lightly_studio.dataset import env as dataset_env
from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.resolvers import collection_resolver


class FakeUvicornServer:
    def __init__(
        self,
        stop_event: threading.Event,
        respect_should_exit: bool = False,
    ) -> None:
        self.started = False
        self.should_exit = False
        self.stop_event = stop_event
        self._respect_should_exit = respect_should_exit

    def run(self) -> None:
        self.started = True
        if self._respect_should_exit:
            while not self.should_exit:
                if self.stop_event.wait(timeout=0.01):
                    break
        else:
            self.stop_event.wait(timeout=1.0)


@pytest.fixture
def patch_gui_background_state(
    mocker: MockerFixture,
) -> Generator[None, None, None]:
    """Patch the background GUI state so each test has a fresh instance."""
    mocker.patch.object(start_gui_module, "_GUI_BACKGROUND_STATE", new=None)
    yield
    state = start_gui_module._GUI_BACKGROUND_STATE
    if state is not None:
        stop_event = getattr(state.uvicorn_server, "stop_event", None)
        if stop_event is not None:
            stop_event.set()
        state.thread.join(timeout=1.0)
        start_gui_module._GUI_BACKGROUND_STATE = None


def test_start_gui__with_samples(
    mocker: MockerFixture,
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    """Test that start_gui works normally when samples exist."""
    image_path = tmp_path / "sample.jpg"
    Image.new("RGB", (10, 10)).save(image_path)

    # Load the dataset using the new Dataset interface
    dataset = ImageDataset.create("test_dataset")
    dataset.add_images_from_path(path=tmp_path)

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
    mock_server_instance.create_uvicorn_server.assert_called_once_with()


def test_start_gui__no_datasets(
    patch_collection: None,  # noqa: ARG001
) -> None:
    """Test that start_gui raises an error when no datasets exist."""
    with pytest.raises(ValueError, match="No datasets found"):
        start_gui()


def test_start_gui__empty_datasets(
    patch_collection: None,  # noqa: ARG001
) -> None:
    """Test that start_gui raises an error when datasets exist but contain no images."""
    # We can't easily create a dataset with no samples using the Dataset class
    # because it validates the path, so we'll create one through the resolver
    # Note: This bypasses the Dataset class's normal creation flow
    session = db_manager.persistent_session()

    collection_resolver.create(
        session=session,
        collection=CollectionCreate(name="empty_dataset_direct", sample_type=SampleType.IMAGE),
    )

    with pytest.raises(ValueError, match="No images have been indexed"):
        start_gui()


def test_start_gui_background(
    mocker: MockerFixture,
    patch_gui_background_state: None,  # noqa: ARG001
) -> None:
    """Ensure a background start sets the background state."""
    # Arrange: Mock server to use our FakeUvicornServer
    mocker.patch.object(
        target=start_gui_module,
        attribute="_validate_has_samples",
    )
    stop_event = threading.Event()
    fake_server = FakeUvicornServer(stop_event=stop_event)
    mocker.patch.object(
        target=Server,
        attribute="create_uvicorn_server",
        return_value=fake_server,
    )

    # Act: Start the GUI in the background
    start_gui_module.start_gui_background()

    # Assert: The background state is set and the server started
    state = start_gui_module._GUI_BACKGROUND_STATE
    assert state is not None
    assert state.thread.is_alive() is True

    stop_event.set()
    state.thread.join(timeout=1.0)


def test_stop_gui_background(
    patch_gui_background_state: None,  # noqa: ARG001
) -> None:
    # Ensure the background server shuts down cleanly on request.
    stop_event = threading.Event()
    fake_server = FakeUvicornServer(stop_event=stop_event, respect_should_exit=True)
    thread = threading.Thread(target=fake_server.run, daemon=True, name="test-gui")
    thread.start()
    state = start_gui_module._GuiBackgroundState(
        uvicorn_server=fake_server,  # type: ignore[arg-type]
        thread=thread,
    )
    start_gui_module._GUI_BACKGROUND_STATE = state

    start_gui_module.stop_gui_background()

    stop_event.set()
    thread.join(timeout=1.0)
    assert start_gui_module._GUI_BACKGROUND_STATE is None
