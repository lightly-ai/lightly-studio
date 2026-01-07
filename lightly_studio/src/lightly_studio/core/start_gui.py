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


@dataclass
class _GuiBackgroundState:
    # Store background execution details so checks/stop can reason about status.
    uvicorn_server: uvicorn.Server
    thread: threading.Thread
    error_queue: Queue[BaseException]
    _error: BaseException | None = None

    @property
    def error(self) -> BaseException | None:
        if self._error is None:
            # Cache the first background exception so later checks report the same failure.
            try:
                self._error = self.error_queue.get_nowait()
            except Empty:
                return None
        return self._error


_GUI_BACKGROUND_STATE: _GuiBackgroundState | None = None


def _raise_background_error_if_exists(state: _GuiBackgroundState, message: str) -> None:
    error = state.error
    if error is None:
        return
    raise RuntimeError(message) from error


def start_gui_background(timeout_s: float = 10.0) -> None:
    """Launch the web interface in a background thread.

    Args:
        timeout_s: How long to wait for the server to start.
    """
    if not isinstance(timeout_s, float) or timeout_s <= 0:
        raise ValueError("timeout_s must be a positive float.")
    global _GUI_BACKGROUND_STATE  # noqa: PLW0603
    if _GUI_BACKGROUND_STATE is not None:
        state = _GUI_BACKGROUND_STATE
        if state.thread.is_alive():
            raise RuntimeError("GUI is already running in the background.")
        _GUI_BACKGROUND_STATE = None
        _raise_background_error_if_exists(
            state=state, message="Previous GUI background server failed."
        )

    _validate_has_samples()

    server = Server(host=env.LIGHTLY_STUDIO_HOST, port=env.LIGHTLY_STUDIO_PORT)
    uvicorn_server = server.create_uvicorn_server()
    error_queue: Queue[BaseException] = Queue()

    def run_server() -> None:
        # Capture startup/runtime errors so the main thread can surface them.
        try:
            uvicorn_server.run()
        except BaseException as exc:
            error_queue.put(exc)

    thread = threading.Thread(
        target=run_server,
        daemon=True,
        name="lightly-studio-gui",
    )
    state = _GuiBackgroundState(
        uvicorn_server=uvicorn_server, thread=thread, error_queue=error_queue
    )
    _GUI_BACKGROUND_STATE = state

    logger.info(f"Open the LightlyStudio GUI under: {env.APP_URL}")

    thread.start()
    # Poll for the uvicorn "started" flag to gate notebook workflows.
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        _raise_background_error_if_exists(
            state=state, message="GUI background server crashed during startup."
        )
        if not thread.is_alive():
            raise RuntimeError("GUI background server stopped before startup completed.")
        if uvicorn_server.started:
            return
        time.sleep(0.05)
    raise TimeoutError(
        f"Timed out waiting for GUI background server to start after {timeout_s:.1f}s."
    )


def check_gui_background() -> None:
    """Check whether the background GUI server is running."""
    state = _GUI_BACKGROUND_STATE
    if state is None:
        raise RuntimeError(
            "GUI is not running in the background. Call start_gui_background() first."
        )

    _raise_background_error_if_exists(
        state=state, message="GUI background server exited with an error."
    )

    if state.uvicorn_server.should_exit or not state.thread.is_alive():
        raise RuntimeError("GUI background server is not running.")

    if not state.uvicorn_server.started:
        raise RuntimeError("GUI background server has not finished starting yet.")


def stop_gui_background(timeout_s: float = 10.0) -> None:
    """Stop the background GUI server."""
    if not isinstance(timeout_s, float) or timeout_s <= 0:
        raise ValueError("timeout_s must be a positive float.")
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
    _raise_background_error_if_exists(
        state=state, message="GUI background server stopped with an error."
    )
