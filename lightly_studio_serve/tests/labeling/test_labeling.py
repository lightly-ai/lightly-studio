from __future__ import annotations

import pytest
from PIL import Image as PILImage
from PIL.Image import Image

from lightly_studio_serve import LabelingModel, ModelTask, PredictedAnnotation


class _CarDetector(LabelingModel):
    @property
    def model_id(self) -> str:
        return "car-detector"

    @property
    def task(self) -> ModelTask:
        return ModelTask.OBJECT_DETECTION

    @property
    def class_names(self) -> list[str]:
        return ["car"]

    def predict(self, image: Image, threshold: float) -> list[PredictedAnnotation]:
        return [
            PredictedAnnotation(
                class_name="car", box=(0.0, 0.0, image.width, image.height), score=threshold
            )
        ]


class _ModelWithoutPredict(LabelingModel):
    @property
    def model_id(self) -> str:
        return "no-predict"

    @property
    def task(self) -> ModelTask:
        return ModelTask.OBJECT_DETECTION

    @property
    def class_names(self) -> list[str]:
        return []


class TestLabelingModel:
    def test_ready__default(self) -> None:
        assert _CarDetector().ready is True

    def test_predict(self) -> None:
        image = PILImage.new(mode="RGB", size=(4, 2))

        predictions = _CarDetector().predict(image=image, threshold=0.5)

        assert predictions == [
            PredictedAnnotation(class_name="car", box=(0.0, 0.0, 4, 2), score=0.5, mask=None)
        ]

    def test_predict__not_implemented(self) -> None:
        with pytest.raises(TypeError, match="predict"):
            _ModelWithoutPredict()  # type: ignore[abstract]
