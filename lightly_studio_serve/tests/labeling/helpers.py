"""A labeling model that the server tests serve."""

from __future__ import annotations

from collections.abc import Sequence

from PIL.Image import Image

from lightly_studio_serve.labeling import LabelingModel, ModelTask, PredictedAnnotation


class FakeLabelingModel(LabelingModel):
    """Returns fixed predictions, or raises, and records what it was handed."""

    def __init__(
        self,
        predictions: list[PredictedAnnotation] | None = None,
        error: Exception | None = None,
        ready: bool = True,
        model_id: str = "car-detector",
        class_names: Sequence[str] = ("car",),
    ) -> None:
        self.predictions = predictions or []
        self.error = error
        self.is_ready = ready
        self.fixed_model_id = model_id
        self.fixed_class_names = list(class_names)
        self.received: list[tuple[tuple[int, int], str, float]] = []

    @property
    def model_id(self) -> str:
        return self.fixed_model_id

    @property
    def task(self) -> ModelTask:
        return ModelTask.OBJECT_DETECTION

    @property
    def class_names(self) -> list[str]:
        return self.fixed_class_names

    @property
    def ready(self) -> bool:
        return self.is_ready

    def predict(self, image: Image, threshold: float) -> list[PredictedAnnotation]:
        self.received.append((image.size, image.mode, threshold))
        if self.error is not None:
            raise self.error
        return self.predictions
