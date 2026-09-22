"""Shared state of the camera demo: camera, bookmarks, training runs and deployment."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID

import torch

from lightly_studio.examples.camera_plugins_demo import dataset_bridge
from lightly_studio.examples.camera_plugins_demo.bookmarks import BookmarkStore
from lightly_studio.examples.camera_plugins_demo.camera import CameraStream, Frame
from lightly_studio.examples.camera_plugins_demo.dataset_bridge import (
    TrainedModelEvaluationConfig,
)
from lightly_studio.examples.camera_plugins_demo.deployment import LiveDetector
from lightly_studio.examples.camera_plugins_demo.integrations import (
    DetectionDispatcher,
    IntegrationSettings,
)
from lightly_studio.examples.camera_plugins_demo.training import RunState, TrainingManager

logger = logging.getLogger(__name__)

MANUAL_CAPTURE = "manual"
AUTO_CAPTURE = "low_confidence"
BOOKMARK_TAG = "bookmarked"
AUTO_CAPTURE_TAG = "low-confidence"
DEFAULT_ANNOTATION_SOURCE = "annotation"
DEFAULT_MODEL = "ltdetrv2-s-coco"


@dataclass
class DemoSettings:
    """Settings of one demo session.

    Attributes:
        source: Camera source: an RTSP or HTTP URL, a webcam index, or a video file.
        data_dir: Directory holding the database, the bookmarks and the training runs.
        dataset_name: Name of the LightlyStudio dataset.
        studio_url: Base URL of the LightlyStudio GUI.
        station_port: Port of the Camera Station page.
        embed: Whether to embed bookmarks for similarity search.
        mqtt_host: MQTT broker host. None turns MQTT off.
        hook_script: Python file with the custom detection callbacks.
        default_model: LightlyTrain model the training operator starts from.
    """

    source: str
    data_dir: Path
    dataset_name: str
    studio_url: str
    station_port: int
    embed: bool = False
    mqtt_host: str | None = None
    mqtt_port: int = 1883
    mqtt_topic: str = "lightly/camera"
    hook_script: Path | None = None
    default_model: str = DEFAULT_MODEL
    default_steps: int = 40
    default_batch_size: int = 4
    default_image_size: int = 448
    default_threshold: float = 0.5


@dataclass
class CameraDemo:
    """Wires the camera, the dataset, the training runs and the live model together.

    One instance lives for the whole demo session. The operators, the Camera Station
    web page and the background threads all read and change this object.
    """

    settings: DemoSettings
    dataset_id: UUID
    collection_id: UUID
    camera: CameraStream
    bookmarks: BookmarkStore
    dispatcher: DetectionDispatcher
    trainings: TrainingManager
    detector: LiveDetector = field(init=False)

    def __post_init__(self) -> None:
        """Create the live detector once the demo parts exist."""
        self.detector = LiveDetector(
            camera=self.camera,
            dispatcher=self.dispatcher,
            auto_capture=self._auto_capture,
        )

    @property
    def grid_url(self) -> str:
        """URL of the image grid of this dataset in LightlyStudio."""
        return (
            f"{self.settings.studio_url}/datasets/{self.dataset_id}"
            f"/image/{self.collection_id}/images"
        )

    def bookmark(self, tags: list[str], capture: str = MANUAL_CAPTURE) -> str:
        """Save the current camera frame as an image sample.

        Returns:
            The file name of the saved frame.

        Raises:
            RuntimeError: If the camera has not delivered a frame yet.
        """
        frame = self.camera.latest_frame()
        if frame is None:
            raise RuntimeError("No camera frame yet. Check the camera source.")
        default_tag = BOOKMARK_TAG if capture == MANUAL_CAPTURE else AUTO_CAPTURE_TAG
        bookmark = self.bookmarks.add(frame=frame, tags=[default_tag, *tags], capture=capture)
        self.dispatcher.log(channel="bookmark", message=bookmark.file_name)
        return bookmark.file_name

    def deploy(self, model: str, threshold: float) -> str:
        """Start a model on the live camera feed.

        Args:
            model: A training run name, "latest" for the newest finished run, or any
                LightlyTrain model name or checkpoint path.
            threshold: Minimum score for a detection.

        Returns:
            A message for the user.

        Raises:
            ValueError: If no trained model is available.
        """
        run_name = model
        if model == "latest":
            latest = self.trainings.latest_completed()
            if latest is None:
                raise ValueError("No finished training run yet. Train a model first.")
            run_name = latest.run_name
        checkpoint = self.trainings.checkpoint_path(run_name=run_name)
        if checkpoint is None and self.trainings.get(run_name=run_name) is not None:
            raise ValueError(f"Run '{run_name}' has no exported model yet.")
        source = str(checkpoint) if checkpoint is not None else model
        self.detector.deploy(model=source, model_name=run_name, threshold=threshold)
        return f"'{run_name}' is running on the camera feed. Watch it at {self.station_url}."

    def stop_deployment(self) -> None:
        """Take the model off the camera feed."""
        self.detector.stop()
        self.dispatcher.log(channel="model", message="Stopped the live model")

    @property
    def station_url(self) -> str:
        """URL of the Camera Station page."""
        return f"http://localhost:{self.settings.station_port}"

    def on_training_completed(self, state: RunState) -> None:
        """Predict on the validation split and create an evaluation run."""
        checkpoint = self.trainings.checkpoint_path(run_name=state.run_name)
        run_config = self.trainings.runs_dir / state.run_name / "run.json"
        if checkpoint is None or not run_config.is_file():
            state.evaluation = "No exported model to evaluate."
            return
        config = json.loads(run_config.read_text())
        val_sample_ids = [UUID(value) for value in config["val_sample_ids"]]
        if not val_sample_ids:
            state.evaluation = "No validation images to evaluate."
            return
        state.evaluation = "Evaluating on the validation split..."
        request = dataset_bridge.EvaluationRequest(
            collection_id=self.collection_id,
            checkpoint=checkpoint,
            sample_ids=val_sample_ids,
            prediction_source=state.run_name,
            ground_truth_source=state.annotation_source or DEFAULT_ANNOTATION_SOURCE,
            evaluation_name=state.run_name,
            score_threshold=self.settings.default_threshold,
        )
        try:
            state.evaluation = dataset_bridge.predict_and_evaluate(
                request=request,
                config=TrainedModelEvaluationConfig(
                    model=state.model,
                    training_steps=state.steps,
                    train_images=state.train_image_count,
                    val_images=state.val_image_count,
                    lightly_train_map_50=state.metrics.get("map_50", 0.0),
                    lightly_train_map=state.metrics.get("map", 0.0),
                    score_threshold=self.settings.default_threshold,
                ),
            )
        except Exception as exc:
            logger.exception("Evaluation failed for %s.", state.run_name)
            state.evaluation = f"Evaluation failed: {exc}"
        self.dispatcher.log(channel="model", message=f"{state.run_name}: {state.evaluation}")

    def state(self) -> dict[str, Any]:
        """Return the full demo state as JSON-compatible data for the station page."""
        camera = self.camera.status()
        deployment = self.detector.status()
        integrations = self.dispatcher.status()
        return {
            "camera": asdict(camera),
            "bookmarks": {
                "count": self.bookmarks.count(),
                "recent": [
                    {
                        "file_name": bookmark.file_name,
                        "tags": list(bookmark.tags),
                        "captured_at": bookmark.captured_at.strftime("%H:%M:%S"),
                    }
                    for bookmark in self.bookmarks.recent()
                ],
            },
            "runs": [
                {
                    **asdict(state),
                    "progress": round(state.progress, 3),
                    "has_model": self.trainings.checkpoint_path(run_name=state.run_name)
                    is not None,
                    "examples": self.trainings.example_images(run_name=state.run_name),
                }
                for state in self.trainings.states()
            ],
            "training_active": self.trainings.is_running(),
            "deployment": {
                **asdict(deployment),
                "detections": [asdict(d) for d in deployment.detections],
            },
            "integrations": {
                **asdict(integrations),
                "events": [asdict(event) for event in integrations.events],
            },
            "links": {"studio": self.settings.studio_url, "grid": self.grid_url},
            "defaults": {
                "model": self.settings.default_model,
                "threshold": self.settings.default_threshold,
            },
        }

    def shutdown(self) -> None:
        """Stop every background worker."""
        self.detector.stop()
        self.trainings.stop()
        self.dispatcher.stop()
        self.camera.stop()

    def _auto_capture(self, frame: Frame) -> None:
        self.bookmarks.add(frame=frame, tags=[AUTO_CAPTURE_TAG], capture=AUTO_CAPTURE)


def build_demo(settings: DemoSettings, dataset_id: UUID, collection_id: UUID) -> CameraDemo:
    """Create the demo state from the settings, without starting anything."""
    camera = CameraStream(source=settings.source)
    bookmarks = BookmarkStore(
        bookmarks_dir=settings.data_dir / "bookmarks",
        collection_id=collection_id,
        camera_name=settings.source,
        embed=settings.embed,
    )
    dispatcher = DetectionDispatcher(
        settings=IntegrationSettings(
            camera_name=settings.source,
            mqtt_host=settings.mqtt_host,
            mqtt_port=settings.mqtt_port,
            mqtt_topic=settings.mqtt_topic,
            hook_script=settings.hook_script,
        )
    )
    demo = CameraDemo(
        settings=settings,
        dataset_id=dataset_id,
        collection_id=collection_id,
        camera=camera,
        bookmarks=bookmarks,
        dispatcher=dispatcher,
        trainings=TrainingManager(runs_dir=settings.data_dir / "runs"),
    )
    demo.trainings.on_completed = demo.on_training_completed
    return demo


def resolve_accelerator() -> str:
    """Return the LightlyTrain accelerator to train on.

    LightlyTrain trains on CUDA or CPU. The backward pass of LT-DETR fails on MPS, so
    Apple silicon trains on the CPU and only runs inference on the GPU.
    """
    return "gpu" if torch.cuda.is_available() else "cpu"
