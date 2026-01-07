"""Tests for start_gui() validation."""

from __future__ import annotations

import threading
from collections.abc import Generator
from pathlib import Path
from queue import Queue

import pytest
from PIL import Image
from pytest_mock import MockerFixture

from lightly_studio import Dataset, db_manager
from lightly_studio.core import start_gui as start_gui_module
from lightly_studio.core.start_gui import start_gui
from lightly_studio.dataset import env as dataset_env
from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.resolvers import collection_resolver


class FakeUvicornServer:
    def __init__(
        self,
        stop_event: threading.Event,
        set_started: bool,
        respect_should_exit: bool = False,
    ) -> None:
        self.started = False
        self.should_exit = False
        self.stop_event = stop_event
        self._set_started = set_started
        self._respect_should_exit = respect_should_exit

    def run(self) -> None:
        if self._set_started:
            self.started = True
        if self._respect_should_exit:
            while not self.should_exit:
                if self.stop_event.wait(timeout=0.01):
                    break
        else:
            self.stop_event.wait(timeout=1.0)


@pytest.fixture
def reset_gui_background_state() -> Generator[None, None, None]:
    start_gui_module._GUI_BACKGROUND_STATE = None
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
    dataset = Dataset.create("test_dataset")
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
    mock_server_instance.start.assert_called_once_with()


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
    reset_gui_background_state: None,  # noqa: ARG001
) -> None:
    """Ensure a background start reports readiness for notebook workflows."""
    # Arrange: Mock server to use our FakeUvicornServer
    mocker.patch.object(
        target=start_gui_module,
        attribute="_validate_has_samples",
    )
    stop_event = threading.Event()
    fake_server = FakeUvicornServer(stop_event=stop_event, set_started=True)
    mock_server = mocker.patch.object(
        target=start_gui_module,
        attribute="Server",
    )
    mock_server.return_value.create_uvicorn_server.return_value = fake_server

    # Act: Start the GUI in the background
    start_gui_module.start_gui_background(timeout_s=0.2)

    # Assert: The background state is set and the server started
    state = start_gui_module._GUI_BACKGROUND_STATE
    assert state is not None
    assert state.uvicorn_server.started is True

    stop_event.set()
    state.thread.join(timeout=1.0)


def test_start_gui_background__startup_timeout(
    mocker: MockerFixture,
    reset_gui_background_state: None,  # noqa: ARG001
) -> None:
    """Ensure a timeout is raised if the background server does not start in time."""
    # Arrange: Mock server to use our FakeUvicornServer with set_started=False
    mocker.patch.object(
        target=start_gui_module,
        attribute="_validate_has_samples",
    )
    stop_event = threading.Event()
    fake_server = FakeUvicornServer(stop_event=stop_event, set_started=False)
    mock_server = mocker.patch.object(
        target=start_gui_module,
        attribute="Server",
    )
    mock_server.return_value.create_uvicorn_server.return_value = fake_server

    # Act & Assert: Starting the GUI should time out
    with pytest.raises(TimeoutError, match="Timed out waiting for GUI background server"):
        start_gui_module.start_gui_background(timeout_s=0.05)

    state = start_gui_module._GUI_BACKGROUND_STATE
    assert state is not None
    stop_event.set()
    state.thread.join(timeout=1.0)
    start_gui_module._GUI_BACKGROUND_STATE = None


def test_check_gui_background(
    reset_gui_background_state: None,  # noqa: ARG001
) -> None:
    # Ensure a running background server passes the health check.
    stop_event = threading.Event()
    fake_server = FakeUvicornServer(stop_event=stop_event, set_started=True)
    thread = threading.Thread(target=fake_server.run, daemon=True, name="test-gui")
    thread.start()
    state = start_gui_module._GuiBackgroundState(
        uvicorn_server=fake_server,  # type: ignore[arg-type]
        thread=thread,
        error_queue=Queue(),
    )
    start_gui_module._GUI_BACKGROUND_STATE = state

    start_gui_module.check_gui_background()

    stop_event.set()
    thread.join(timeout=1.0)
    start_gui_module._GUI_BACKGROUND_STATE = None


def test_check_gui_background__not_running(
    reset_gui_background_state: None,  # noqa: ARG001
) -> None:
    # Ensure a helpful error is raised when no background server was started.
    with pytest.raises(RuntimeError, match="GUI is not running in the background"):
        start_gui_module.check_gui_background()


def test_stop_gui_background(
    reset_gui_background_state: None,  # noqa: ARG001
) -> None:
    # Ensure the background server shuts down cleanly on request.
    stop_event = threading.Event()
    fake_server = FakeUvicornServer(
        stop_event=stop_event,
        set_started=True,
        respect_should_exit=True,
    )
    thread = threading.Thread(target=fake_server.run, daemon=True, name="test-gui")
    thread.start()
    state = start_gui_module._GuiBackgroundState(
        uvicorn_server=fake_server,  # type: ignore[arg-type]
        thread=thread,
        error_queue=Queue(),
    )
    start_gui_module._GUI_BACKGROUND_STATE = state

    start_gui_module.stop_gui_background(timeout_s=0.5)

    stop_event.set()
    thread.join(timeout=1.0)
    assert start_gui_module._GUI_BACKGROUND_STATE is None


def test_stop_gui_background__timeout(
    reset_gui_background_state: None,  # noqa: ARG001
) -> None:
    # Ensure a timeout is raised if the background thread does not stop promptly.
    stop_event = threading.Event()
    fake_server = FakeUvicornServer(stop_event=stop_event, set_started=True)
    thread = threading.Thread(target=fake_server.run, daemon=True, name="test-gui")
    thread.start()
    state = start_gui_module._GuiBackgroundState(
        uvicorn_server=fake_server,  # type: ignore[arg-type]
        thread=thread,
        error_queue=Queue(),
    )
    start_gui_module._GUI_BACKGROUND_STATE = state

    with pytest.raises(TimeoutError, match="Timed out waiting for GUI background server"):
        start_gui_module.stop_gui_background(timeout_s=0.01)

    stop_event.set()
    thread.join(timeout=1.0)
    start_gui_module._GUI_BACKGROUND_STATE = None
