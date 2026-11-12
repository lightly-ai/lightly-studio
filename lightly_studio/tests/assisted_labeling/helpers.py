"""Helpers for the assisted labeling tests."""

from __future__ import annotations

import io
from collections.abc import Sequence
from uuid import UUID

from lightly_studio_serve.labeling_model import LabelingModel, ModelTask
from lightly_studio_serve.types import PredictedAnnotation
from PIL import Image as PILImage
from PIL.Image import Image

from lightly_studio.assisted_labeling.provider import (
    BoxPrompt,
    PointPrompt,
    ProviderImage,
    SegmentationPrompt,
)

DEFAULT_SAMPLE_ID = UUID(int=1)


def make_image(
    width: int,
    height: int,
    sample_id: UUID = DEFAULT_SAMPLE_ID,
    file_name: str = "image.jpg",
    data: bytes = b"image-bytes",
) -> ProviderImage:
    return ProviderImage(
        sample_id=sample_id,
        width=width,
        height=height,
        file_name=file_name,
        read_bytes=lambda: data,
    )


def make_prompt(
    points: list[PointPrompt] | None = None,
    boxes: list[BoxPrompt] | None = None,
    text: str | None = None,
    max_masks: int = 1,
) -> SegmentationPrompt:
    return SegmentationPrompt(
        points=points or [],
        boxes=boxes or [],
        text=text,
        max_masks=max_masks,
    )


class StubLabelingModel(LabelingModel):
    """A labeling model that records its inputs, then returns fixed predictions or raises."""

    def __init__(
        self,
        model_id: str,
        task: ModelTask = ModelTask.OBJECT_DETECTION,
        class_names: Sequence[str] = (),
        predictions: Sequence[PredictedAnnotation] = (),
        error: Exception | None = None,
    ) -> None:
        self._model_id = model_id
        self._task = task
        self._class_names = list(class_names)
        self._predictions = list(predictions)
        self._error = error
        self.images: list[Image] = []
        self.thresholds: list[float] = []

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def task(self) -> ModelTask:
        return self._task

    @property
    def class_names(self) -> list[str]:
        return self._class_names

    def predict(
        self,
        image: Image,
        threshold: float,
    ) -> list[PredictedAnnotation]:
        self.images.append(image)
        self.thresholds.append(threshold)
        if self._error is not None:
            raise self._error
        return self._predictions


def png_bytes(width: int, height: int) -> bytes:
    """Return the content of a black PNG file of the size."""
    buffer = io.BytesIO()
    PILImage.new(mode="RGB", size=(width, height)).save(buffer, format="PNG")
    return buffer.getvalue()
