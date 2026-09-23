"""Run a trained model on the live camera feed."""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import lightly_train  # type: ignore[import-not-found]
import numpy as np
import torch
from numpy.typing import NDArray
from torch import Tensor

from lightly_studio.examples.camera_plugins_demo.camera import CameraStream, Frame
from lightly_studio.examples.camera_plugins_demo.integrations import (
    Detection,
    DetectionDispatcher,
)

logger = logging.getLogger(__name__)

_FPS_WINDOW_S = 3.0
_BOX_COLORS = [
    (86, 220, 140),
    (255, 176, 59),
    (120, 176, 255),
    (240, 120, 200),
    (255, 232, 92),
    (140, 240, 240),
]


@dataclass(frozen=True)
class AutoCaptureSettings:
    """When to bookmark a frame that the deployed model is unsure about.

    Attributes:
        threshold: A frame is captured when every box scores below this value.
        interval_s: Shortest time between two captures.
    """

    threshold: float = 0.6
    interval_s: float = 5.0


@dataclass
class DeploymentStatus:
    """State of the model that runs on the camera feed."""

    active: bool
    loading: bool
    model_name: str
    device: str
    threshold: float
    fps: float
    error: str
    auto_capture: bool
    auto_capture_count: int
    detections: list[Detection] = field(default_factory=list)


class LiveDetector:
    """Runs a LightlyTrain model on camera frames in a background thread.

    The detector keeps the newest detections so that the video stream can draw them
    over the live frames, and it hands every result to the integrations dispatcher.

    Frames whose detections are all below `auto_capture_threshold` are handed to
    `auto_capture`, which bookmarks them. That closes the data loop: the cases the
    deployed model is unsure about come back into the dataset for labeling.
    """

    def __init__(
        self,
        camera: CameraStream,
        dispatcher: DetectionDispatcher,
        device: str,
        auto_capture: Callable[[Frame], None] | None = None,
        auto_capture_settings: AutoCaptureSettings | None = None,
    ) -> None:
        """Create a detector for a camera, without loading a model yet."""
        settings = auto_capture_settings or AutoCaptureSettings()
        self._camera = camera
        self._requested_device = device
        self._dispatcher = dispatcher
        self._auto_capture = auto_capture
        self._auto_capture_threshold = settings.threshold
        self._auto_capture_interval_s = settings.interval_s
        self._auto_capture_enabled = False
        self._auto_capture_count = 0
        self._last_auto_capture = 0.0

        self._model_name = ""
        self._device = ""
        self._threshold = 0.5
        self._error = ""
        self._loading = False
        self._detections: list[Detection] = []
        self._inference_times: list[float] = []
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def deploy(self, model: str, model_name: str, threshold: float) -> None:
        """Load a model and start running it on the camera feed.

        Args:
            model: LightlyTrain model name or path to an exported checkpoint.
            model_name: Display name, usually the training run name.
            threshold: Minimum score for a detection to count.
        """
        self.stop()
        self._model_name = model_name
        self._threshold = threshold
        self._error = ""
        self._loading = True
        self._dispatcher.reset()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(
            target=self._run,
            kwargs={"model": model},
            name="live-detector",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop the inference thread."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=10)
            self._thread = None
        with self._lock:
            self._detections = []
        self._model_name = ""
        self._loading = False

    def set_auto_capture(self, enabled: bool) -> None:
        """Turn bookmarking of low-confidence frames on or off."""
        self._auto_capture_enabled = enabled

    def status(self) -> DeploymentStatus:
        """Return a snapshot of the deployment for the UI."""
        now = time.monotonic()
        recent = [t for t in self._inference_times if now - t <= _FPS_WINDOW_S]
        with self._lock:
            detections = list(self._detections)
        return DeploymentStatus(
            active=self._thread is not None and self._thread.is_alive(),
            loading=self._loading,
            model_name=self._model_name,
            device=self._device,
            threshold=self._threshold,
            fps=round(len(recent) / _FPS_WINDOW_S, 1),
            error=self._error,
            auto_capture=self._auto_capture_enabled,
            auto_capture_count=self._auto_capture_count,
            detections=detections,
        )

    def draw_overlay(self, image: NDArray[np.uint8]) -> NDArray[np.uint8]:
        """Return a copy of the image with the newest detections drawn on it."""
        with self._lock:
            detections = list(self._detections)
        if not detections:
            return image
        annotated = image.copy()
        for detection in detections:
            color = _BOX_COLORS[hash(detection.class_name) % len(_BOX_COLORS)]
            x1, y1, x2, y2 = detection.box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            caption = f"{detection.class_name} {detection.score:.2f}"
            (text_w, text_h), _ = cv2.getTextSize(caption, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            top = max(0, y1 - text_h - 6)
            cv2.rectangle(annotated, (x1, top), (x1 + text_w + 6, top + text_h + 6), color, -1)
            cv2.putText(
                annotated,
                caption,
                (x1 + 3, top + text_h + 1),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (20, 20, 20),
                1,
                cv2.LINE_AA,
            )
        return annotated

    def _run(self, model: str) -> None:
        try:
            loaded = lightly_train.load_model(model=model, device=self._requested_device)
            self._device = str(next(loaded.parameters()).device)
        except Exception as exc:
            self._error = f"Failed to load model: {exc}"
            self._loading = False
            logger.exception("Failed to load model '%s'.", model)
            return
        self._loading = False
        self._dispatcher.log(
            channel="model", message=f"{self._model_name} is live ({self._device})"
        )
        logger.info("Model %s is live on %s.", self._model_name, self._device)

        class_names: dict[int, str] = dict(loaded.classes)
        last_index = -1
        while not self._stop_event.is_set():
            frame = self._camera.wait_for_frame(after_index=last_index, timeout=1.0)
            if frame is None:
                continue
            last_index = frame.index
            rgb = cv2.cvtColor(frame.image, cv2.COLOR_BGR2RGB)
            tensor = torch.from_numpy(rgb).permute(2, 0, 1)
            try:
                prediction = loaded.predict(tensor, threshold=self._threshold)
            except Exception as exc:
                self._error = f"Inference failed: {exc}"
                logger.exception("Inference failed.")
                break
            detections = _to_detections(prediction=prediction, class_names=class_names)
            with self._lock:
                self._detections = detections
            now = time.monotonic()
            self._inference_times = [t for t in self._inference_times if now - t <= _FPS_WINDOW_S]
            self._inference_times.append(now)
            self._dispatcher.submit(
                model_name=self._model_name, frame_index=frame.index, detections=detections
            )
            self._maybe_auto_capture(frame=frame, detections=detections)

    def _maybe_auto_capture(self, frame: Frame, detections: list[Detection]) -> None:
        if not self._auto_capture_enabled or self._auto_capture is None or not detections:
            return
        if max(d.score for d in detections) >= self._auto_capture_threshold:
            return
        if time.monotonic() - self._last_auto_capture < self._auto_capture_interval_s:
            return
        self._last_auto_capture = time.monotonic()
        try:
            self._auto_capture(frame)
        except Exception:
            logger.exception("Auto-capture failed.")
            return
        self._auto_capture_count += 1
        self._dispatcher.log(channel="curation", message="Bookmarked a low-confidence frame")


def resolve_model_source(model: str, checkpoint: Path | None) -> str:
    """Return the checkpoint path if there is one, else the model name."""
    return str(checkpoint) if checkpoint is not None else model


def _to_detections(
    prediction: Mapping[str, Tensor], class_names: dict[int, str]
) -> list[Detection]:
    labels = prediction["labels"].detach().cpu().tolist()
    boxes = prediction["bboxes"].detach().cpu().tolist()
    scores = prediction["scores"].detach().cpu().tolist()
    detections = []
    for label, box, score in zip(labels, boxes, scores):
        x1, y1, x2, y2 = (round(value) for value in box)
        detections.append(
            Detection(
                class_name=class_names.get(label, str(label)),
                score=float(score),
                box=(x1, y1, x2, y2),
            )
        )
    return detections
