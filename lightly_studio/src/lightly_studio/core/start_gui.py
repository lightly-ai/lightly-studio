"""Module to launch the GUI."""

from __future__ import annotations

import asyncio
import logging
import threading
from dataclasses import dataclass

import uvicorn

from lightly_studio import db_manager
from lightly_studio.api.server import Server
from lightly_studio.dataset import env
from lightly_studio.resolvers import collection_resolver, sample_resolver

logger = logging.getLogger(__name__)


def start_gui() -> None:
    """Launch the web interface for the loaded dataset.

    This call blocks until the server stops.
    """
    _validate_has_samples()

    server = Server(host=env.LIGHTLY_STUDIO_HOST, port=env.LIGHTLY_STUDIO_PORT)
    uvicorn_server = server.create_uvicorn_server()

    logger.info(f"Open the LightlyStudio GUI under: {env.APP_URL}")

    _run_uvicorn_server(uvicorn_server)


@dataclass
class _GuiBackgroundState:
    # Store background execution details so stop can target the right server.
    uvicorn_server: uvicorn.Server
    thread: threading.Thread


_GUI_BACKGROUND_STATE: _GuiBackgroundState | None = None


def start_gui_background() -> None:
    """Launch the web interface in a background thread."""
    global _GUI_BACKGROUND_STATE  # noqa: PLW0603
    # TODO(Malte, 01/26): Handle start when a background server is already running.

    _validate_has_samples()

    server = Server(host=env.LIGHTLY_STUDIO_HOST, port=env.LIGHTLY_STUDIO_PORT)
    uvicorn_server = server.create_uvicorn_server()

    thread = threading.Thread(
        target=_run_uvicorn_server,
        args=(uvicorn_server,),
        daemon=True,
        name="lightly-studio-gui",
    )
    state = _GuiBackgroundState(uvicorn_server=uvicorn_server, thread=thread)
    _GUI_BACKGROUND_STATE = state

    logger.info(f"Open the LightlyStudio GUI under: {env.APP_URL}")

    thread.start()
    # TODO(Malte, 01/26): Wait for server startup and surface background errors.


def stop_gui_background() -> None:
    """Stop the background GUI server."""
    global _GUI_BACKGROUND_STATE  # noqa: PLW0603
    state = _GUI_BACKGROUND_STATE
    if state is None:
        # TODO(Malte, 01/26): Handle stop when no background server is running.
        return

    state.uvicorn_server.should_exit = True
    state.thread.join()
    _GUI_BACKGROUND_STATE = None
    # TODO(Malte, 01/26): Handle background server shutdown failures.


def _run_uvicorn_server(uvicorn_server: uvicorn.Server) -> None:
    """Start a Uvicorn server, handling notebook event loops."""
    # Notebook environments (Colab/Jupyter) already run an event loop.
    # We do this to support running the app in a notebook environment.
    # Reuse the same server instance so serve/run share the same lifecycle state.
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        loop.create_task(uvicorn_server.serve())
        return

    # start the app with connection limits and timeouts
    uvicorn_server.run()


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
