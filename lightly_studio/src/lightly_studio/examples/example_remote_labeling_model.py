"""Example of labeling images in the GUI with a model on a remote server.

A subprocess serves ``CenterBoxModel`` with ``lightly_studio_serve.serve``.
``ls.register_remote_labeling_model`` saves the URL and the API key of the server in the
dataset. Open an image, turn on edit mode and select "Label with model" in the toolbar.
The model suggests one box in the center of the image, so no weights are downloaded.
"""

from __future__ import annotations

import multiprocessing
import secrets
import time

import httpx
import lightly_studio_serve
from environs import Env
from lightly_studio_serve import labeling_protocol
from PIL.Image import Image

import lightly_studio as ls
from lightly_studio.database import db_manager

SERVER_PORT = 8080
SERVER_URL = f"http://127.0.0.1:{SERVER_PORT}"
SERVER_STARTUP_TIMEOUT_SECONDS = 30.0


class CenterBoxModel(ls.LabelingModel):
    """Suggests one box in the center of the image. Runs on the server."""

    @property
    def model_id(self) -> str:
        """The model name, shown in the GUI."""
        return "example/center-box"

    @property
    def task(self) -> ls.ModelTask:
        """The model predicts boxes."""
        return ls.ModelTask.OBJECT_DETECTION

    @property
    def class_names(self) -> list[str]:
        """The single annotation class of the model."""
        return ["center"]

    def predict(
        self,
        image: Image,
        threshold: float,  # noqa: ARG002
    ) -> list[ls.PredictedAnnotation]:
        """Predict a box that covers the middle half of the image."""
        width, height = image.size
        box = (width / 4, height / 4, 3 * width / 4, 3 * height / 4)
        return [ls.PredictedAnnotation(class_name="center", box=box, score=0.9)]


def main() -> None:
    """Start the server, create the dataset and start the GUI."""
    env = Env()
    env.read_env()
    api_key = secrets.token_urlsafe()

    server = multiprocessing.Process(target=_serve, kwargs={"api_key": api_key}, daemon=True)
    server.start()
    _wait_for_server(server=server, api_key=api_key)

    db_manager.connect(cleanup_existing=True)
    dataset = ls.ImageDataset.create()
    dataset.add_images_from_path(path=env.path("EXAMPLES_DATASET_PATH"))
    # The dataset stores the URL and the API key, so a later process needs no registration
    ls.register_remote_labeling_model(dataset=dataset, url=SERVER_URL, api_key=api_key)
    ls.start_gui()


def _serve(api_key: str) -> None:
    """Serve the model until the process stops."""
    lightly_studio_serve.serve(labeling_model=CenterBoxModel(), port=SERVER_PORT, api_key=api_key)


def _wait_for_server(server: multiprocessing.Process, api_key: str) -> None:
    """Wait until the server answers its describe endpoint.

    Raises:
        RuntimeError: If the server stops, or does not answer in time.
    """
    deadline = time.monotonic() + SERVER_STARTUP_TIMEOUT_SECONDS
    url = f"{SERVER_URL}{labeling_protocol.LABELING_DESCRIBE_PATH}"
    headers = {"Authorization": f"Bearer {api_key}"}
    while time.monotonic() < deadline:
        if not server.is_alive():
            raise RuntimeError("The labeling server stopped before it answered.")
        try:
            if httpx.get(url, headers=headers, timeout=1.0).is_success:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.2)
    raise RuntimeError(f"The labeling server did not answer at {SERVER_URL}.")


if __name__ == "__main__":
    main()
