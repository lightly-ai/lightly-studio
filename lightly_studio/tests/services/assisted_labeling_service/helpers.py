"""Helpers for the assisted labeling service tests."""

from __future__ import annotations

from lightly_studio.assisted_labeling.labeling_model import (
    LabelingImage,
    LabelingModel,
    ModelTask,
    PredictedAnnotation,
)
from lightly_studio.assisted_labeling.provider import Prediction, SegmentationPrompt


class StubProvider:
    """Provider that records the prompts and returns fixed predictions or raises an error."""

    vendor = "stub-vendor"
    model = "stub-model"

    def __init__(
        self, predictions: list[Prediction] | None = None, error: Exception | None = None
    ) -> None:
        self.predictions = predictions or []
        self.error = error
        self.prompts: list[SegmentationPrompt] = []

    def unavailable_reason(self) -> str | None:
        return None

    def segment(self, image: LabelingImage, prompt: SegmentationPrompt) -> list[Prediction]:  # noqa: ARG002
        self.prompts.append(prompt)
        if self.error is not None:
            raise self.error
        return self.predictions


class StubLabelingModel(LabelingModel):
    """Labeling model that records the thresholds and returns fixed predictions or raises."""

    def __init__(
        self,
        predictions: list[PredictedAnnotation] | None = None,
        model_id: str = "stub-model",
        task: ModelTask = ModelTask.OBJECT_DETECTION,
        class_names: list[str] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.predictions = predictions or []
        self._model_id = model_id
        self._task = task
        self._class_names = class_names or []
        self.error = error
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

    @property
    def vendor(self) -> str:
        return "stub-vendor"

    def predict(self, image: LabelingImage, threshold: float) -> list[PredictedAnnotation]:  # noqa: ARG002
        self.thresholds.append(threshold)
        if self.error is not None:
            raise self.error
        return self.predictions
