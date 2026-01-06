"""Module to launch the GUI."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from queue import Empty, Queue
from typing import TYPE_CHECKING

from lightly_studio import db_manager
from lightly_studio.api.server import Server
from lightly_studio.dataset import env
from lightly_studio.resolvers import collection_resolver, sample_resolver

logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    import uvicorn


@dataclass
class _GuiBackgroundState:
    uvicorn_server: uvicorn.Server
    thread: threading.Thread
    error_queue: Queue[BaseException]
    error: BaseException | None = None


_GUI_BACKGROUND_STATE: _GuiBackgroundState | None = None


def _validate_has_samples() -> None:
    """Validate that there are samples in the database before starting GUI.

    Raises:
        ValueError: If no datasets are found or if no samples exist in any dataset.
    """
    session = db_manager.persistent_session()

    # Check if any datasets exist
    datasets = collection_resolver.get_all(session=session, offset=0, limit=1)

    if not datasets:
        raise ValueError(
            "No datasets found. Please load a dataset using Dataset class methods "
            "(e.g., add_images_from_path(), add_samples_from_yolo(), etc.) "
            "before starting the GUI."
        )

    # Check if there are any samples in the first dataset
    first_dataset = datasets[0]
    sample_count = sample_resolver.count_by_collection_id(
        session=session, collection_id=first_dataset.collection_id
    )

    if sample_count == 0:
        raise ValueError(
            "No images have been indexed for the first dataset. "
            "Please ensure your dataset contains valid images and try loading again."
        )


def start_gui() -> None:
    """Launch the web interface for the loaded dataset.

    This call blocks until the server stops.
    """
    _validate_has_samples()

    server = Server(host=env.LIGHTLY_STUDIO_HOST, port=env.LIGHTLY_STUDIO_PORT)

    logger.info(f"Open the LightlyStudio GUI under: {env.APP_URL}")

    server.start()


def _run_uvicorn_server(
    uvicorn_server: uvicorn.Server, error_queue: Queue[BaseException]
) -> None:
    try:
        uvicorn_server.run()
    except BaseException as exc:
        error_queue.put(exc)


def _get_background_error(state: _GuiBackgroundState) -> BaseException | None:
    if state.error is not None:
        return state.error
    try:
        state.error = state.error_queue.get_nowait()
    except Empty:
        return None
    return state.error


def _raise_background_error(state: _GuiBackgroundState, message: str) -> None:
    error = _get_background_error(state)
    if error is None:
        return
    raise RuntimeError(message) from error


def _wait_for_background_start(state: _GuiBackgroundState, timeout_s: float) -> None:
    if timeout_s <= 0:
        return
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        _raise_background_error(state, "GUI background server crashed during startup.")
        if not state.thread.is_alive():
            raise RuntimeError("GUI background server stopped before startup completed.")
        if state.uvicorn_server.started:
            return
        time.sleep(0.05)
    raise TimeoutError(
        f"Timed out waiting for GUI background server to start after {timeout_s:.1f}s."
    )


def start_gui_background(timeout_s: float | None = 10.0) -> None:
    """Launch the web interface in a background thread.

    Args:
        timeout_s: How long to wait for the server to start. Set to None to skip waiting.
    """
    global _GUI_BACKGROUND_STATE  # noqa: PLW0603
    if _GUI_BACKGROUND_STATE is not None:
        state = _GUI_BACKGROUND_STATE
        if state.thread.is_alive():
            raise RuntimeError("GUI is already running in the background.")
        _GUI_BACKGROUND_STATE = None
        _raise_background_error(state, "Previous GUI background server failed.")

    _validate_has_samples()

    server = Server(host=env.LIGHTLY_STUDIO_HOST, port=env.LIGHTLY_STUDIO_PORT)
    uvicorn_server = server.create_uvicorn_server()
    error_queue: Queue[BaseException] = Queue()
    thread = threading.Thread(
        target=_run_uvicorn_server,
        args=(uvicorn_server, error_queue),
        daemon=True,
        name="lightly-studio-gui",
    )
    state = _GuiBackgroundState(
        uvicorn_server=uvicorn_server, thread=thread, error_queue=error_queue
    )
    _GUI_BACKGROUND_STATE = state

    logger.info(f"Open the LightlyStudio GUI under: {env.APP_URL}")

    thread.start()
    if timeout_s is not None:
        _wait_for_background_start(state, timeout_s)


def check_gui_background() -> None:
    """Check whether the background GUI server is running."""
    state = _GUI_BACKGROUND_STATE
    if state is None:
        raise RuntimeError(
            "GUI is not running in the background. Call start_gui_background() first."
        )

    _raise_background_error(state, "GUI background server exited with an error.")

    if state.uvicorn_server.should_exit or not state.thread.is_alive():
        raise RuntimeError("GUI background server is not running.")

    if not state.uvicorn_server.started:
        raise RuntimeError("GUI background server has not finished starting yet.")


def stop_gui_background(timeout_s: float = 10.0) -> None:
    """Stop the background GUI server."""
    global _GUI_BACKGROUND_STATE  # noqa: PLW0603
    state = _GUI_BACKGROUND_STATE
    if state is None:
        raise RuntimeError("GUI is not running in the background.")

    state.uvicorn_server.should_exit = True
    state.thread.join(timeout=timeout_s)
    if state.thread.is_alive():
        raise TimeoutError(
            f"Timed out waiting for GUI background server to stop after {timeout_s:.1f}s."
        )

    _GUI_BACKGROUND_STATE = None
    _raise_background_error(state, "GUI background server stopped with an error.")
