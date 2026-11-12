from __future__ import annotations

import numpy as np
import pytest
from pydantic import ValidationError

from lightly_studio_serve import labeling_protocol
from lightly_studio_serve.labeling_model import ModelTask
from lightly_studio_serve.labeling_protocol import (
    LabelingDescribeResponse,
    PredictionsResponse,
    WirePrediction,
)
from lightly_studio_serve.protocol import ServerLimits
from lightly_studio_serve.types import PredictedAnnotation


def test_labeling_describe_response() -> None:
    response = LabelingDescribeResponse(
        model_id="car-detector",
        task=ModelTask.OBJECT_DETECTION,
        class_names=["car"],
        ready=True,
        limits=ServerLimits(),
    )

    assert response.protocol_version == "1.0"
    assert response.model_dump(mode="json")["task"] == "object_detection"


def test_labeling_describe_response__empty_model_id() -> None:
    with pytest.raises(ValidationError, match="model_id"):
        LabelingDescribeResponse(
            model_id="",
            task=ModelTask.OBJECT_DETECTION,
            class_names=["car"],
            ready=True,
            limits=ServerLimits(),
        )


def test_predictions_response__json_round_trip() -> None:
    response = PredictionsResponse(
        model_id="car-detector",
        predictions=[WirePrediction(class_name="car", box=(1.0, 2.0, 3.0, 4.0), score=0.9)],
    )

    restored = PredictionsResponse.model_validate_json(response.model_dump_json())

    assert restored == response
    assert restored.predictions[0].mask_png is None


def test_to_wire_prediction__box() -> None:
    prediction = PredictedAnnotation(class_name="car", box=(1.0, 2.0, 3.0, 4.0), score=0.9)

    wire = labeling_protocol.to_wire_prediction(prediction=prediction)

    assert wire == WirePrediction(
        class_name="car", box=(1.0, 2.0, 3.0, 4.0), score=0.9, mask_png=None
    )
    assert labeling_protocol.from_wire_prediction(prediction=wire) == prediction


def test_to_wire_prediction__mask_round_trip() -> None:
    # 2 rows and 3 columns, so a swap of height and width is visible.
    mask = np.array([[True, False, False], [False, True, True]], dtype=np.bool_)
    prediction = PredictedAnnotation(
        class_name="car", box=(0.0, 0.0, 3.0, 2.0), score=0.9, mask=mask
    )

    wire = labeling_protocol.to_wire_prediction(prediction=prediction)
    restored = labeling_protocol.from_wire_prediction(prediction=wire)

    assert wire.mask_png is not None
    assert restored.mask is not None
    assert restored.mask.dtype == np.bool_
    assert restored.mask.shape == (2, 3)
    np.testing.assert_array_equal(restored.mask, mask)


@pytest.mark.parametrize(
    "mask",
    [
        pytest.param(np.ones((2, 3), dtype=np.float32), id="float"),
        pytest.param(np.ones((1, 2, 3), dtype=np.bool_), id="three-dimensions"),
    ],
)
def test_to_wire_prediction__invalid_mask(mask: np.ndarray) -> None:  # type: ignore[type-arg]
    prediction = PredictedAnnotation(
        class_name="car", box=(0.0, 0.0, 3.0, 2.0), score=0.9, mask=mask
    )

    with pytest.raises(ValueError, match="not a boolean array with two dimensions"):
        labeling_protocol.to_wire_prediction(prediction=prediction)


def test_to_wire_prediction__score_not_finite() -> None:
    prediction = PredictedAnnotation(class_name="car", box=(0.0, 0.0, 3.0, 2.0), score=float("nan"))

    with pytest.raises(ValidationError, match="score"):
        labeling_protocol.to_wire_prediction(prediction=prediction)


@pytest.mark.parametrize("mask_png", ["not base64!", "aGVsbG8="])
def test_from_wire_prediction__invalid_mask(mask_png: str) -> None:
    wire = WirePrediction(class_name="car", box=(0.0, 0.0, 3.0, 2.0), score=0.9, mask_png=mask_png)

    with pytest.raises(ValueError, match="not a base64 PNG file"):
        labeling_protocol.from_wire_prediction(prediction=wire)
