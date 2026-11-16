from __future__ import annotations

import pytest
from lightly_studio_serve.labeling import ModelTask, PredictedAnnotation

from lightly_studio.assisted_labeling.labeling_model_runner import LocalLabelingModelRunner
from lightly_studio.assisted_labeling.provider import ProviderError, ProviderNotCalledError
from tests.assisted_labeling import helpers
from tests.assisted_labeling.helpers import StubLabelingModel


class TestLocalLabelingModelRunner:
    def test_properties(self) -> None:
        model = StubLabelingModel(
            model_id="m", task=ModelTask.INSTANCE_SEGMENTATION, class_names=["car", "person"]
        )

        runner = LocalLabelingModelRunner(model=model)

        assert runner.model_id == "m"
        assert runner.task is ModelTask.INSTANCE_SEGMENTATION
        assert runner.class_names == ["car", "person"]

    def test_predict(self) -> None:
        prediction = PredictedAnnotation(class_name="car", box=(1.0, 2.0, 3.0, 4.0), score=0.9)
        model = StubLabelingModel(model_id="m", predictions=[prediction])
        image = helpers.make_image(width=4, height=2, data=helpers.png_bytes(width=4, height=2))

        predictions = LocalLabelingModelRunner(model=model).predict(image=image, threshold=0.3)

        assert predictions == [prediction]
        assert model.thresholds == [0.3]
        (pil_image,) = model.images
        assert pil_image.size == (4, 2)
        assert pil_image.mode == "RGB"

    def test_predict__model_error(self, caplog: pytest.LogCaptureFixture) -> None:
        model = StubLabelingModel(model_id="m", error=RuntimeError("secret output"))
        image = helpers.make_image(width=4, height=2, data=helpers.png_bytes(width=4, height=2))

        with pytest.raises(ProviderError) as error_info:
            LocalLabelingModelRunner(model=model).predict(image=image, threshold=0.3)

        assert str(error_info.value) == (
            "The labeling model 'm' raised RuntimeError. See the server log."
        )
        assert not isinstance(error_info.value, ProviderNotCalledError)
        assert "secret output" in caplog.text

    def test_predict__image_not_decodable(self) -> None:
        model = StubLabelingModel(model_id="m")
        image = helpers.make_image(width=4, height=2, file_name="a.jpg", data=b"not an image")

        with pytest.raises(ProviderNotCalledError, match=r"'a\.jpg' cannot be decoded"):
            LocalLabelingModelRunner(model=model).predict(image=image, threshold=0.3)

        assert model.images == []
