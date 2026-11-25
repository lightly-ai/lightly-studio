from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pytest
from lightly_studio_serve.labeling import ModelTask, PredictedAnnotation

from lightly_studio.assisted_labeling import predicted_annotation_checks
from lightly_studio.assisted_labeling.provider import ProviderError

WIDTH = 4
HEIGHT = 2
FULL_BOX = (0.0, 0.0, 4.0, 2.0)


def test_check_predictions__object_detection() -> None:
    predicted_annotation_checks.check_predictions(
        predictions=[
            PredictedAnnotation(class_name="cat", box=FULL_BOX, score=0.0),
            PredictedAnnotation(class_name="dog", box=(-3.5, -1.0, 9.0, 5.0), score=1.0),
        ],
        task=ModelTask.OBJECT_DETECTION,
        class_names=["cat", "dog"],
        width=WIDTH,
        height=HEIGHT,
    )


def test_check_predictions__integers_and_numpy_scalars() -> None:
    predicted_annotation_checks.check_predictions(
        predictions=[
            PredictedAnnotation(class_name="cat", box=(0, 0, 4, 2), score=1),
            _make_prediction(
                fields={
                    "box": (np.float32(0.5), np.float32(0.5), np.int64(4), np.int64(2)),
                    "score": np.float32(0.8),
                }
            ),
        ],
        task=ModelTask.OBJECT_DETECTION,
        class_names=["cat"],
        width=WIDTH,
        height=HEIGHT,
    )


def test_check_predictions__instance_segmentation() -> None:
    predicted_annotation_checks.check_predictions(
        predictions=[
            PredictedAnnotation(
                class_name="cat",
                box=FULL_BOX,
                score=0.8,
                mask=np.zeros((HEIGHT, WIDTH), dtype=np.bool_),
            )
        ],
        task=ModelTask.INSTANCE_SEGMENTATION,
        class_names=["cat"],
        width=WIDTH,
        height=HEIGHT,
    )


@pytest.mark.parametrize(
    ("fields", "message"),
    [
        pytest.param({"score": float("nan")}, r"a score that is not", id="score-nan"),
        pytest.param({"score": 1.5}, r"a score that is not", id="score-above-1"),
        pytest.param({"score": -0.1}, r"a score that is not", id="score-below-0"),
        pytest.param({"score": "0.8"}, r"a score that is not", id="score-str"),
        pytest.param({"score": None}, r"a score that is not", id="score-none"),
        pytest.param({"score": True}, r"a score that is not", id="score-bool"),
        pytest.param({"class_name": "dog"}, r"an annotation class that", id="class-unknown"),
        pytest.param({"class_name": ["cat"]}, r"an annotation class that", id="class-list"),
        pytest.param({"box": (0.0, 0.0, float("inf"), 2.0)}, r"a box that is not", id="box-inf"),
        pytest.param({"box": (0.0, 0.0, 4.0, 2.0, 1.0)}, r"a box that is not", id="box-5-values"),
        pytest.param({"box": ("0", "0", "4", "2")}, r"a box that is not", id="box-str-values"),
        pytest.param({"box": None}, r"a box that is not", id="box-none"),
        pytest.param({"box": (3.0, 0.0, 1.0, 2.0)}, r"a positive size", id="box-inverted"),
        pytest.param({"box": (1.0, 1.0, 3.0, 1.0)}, r"a positive size", id="box-empty"),
        pytest.param(
            {"mask": np.ones((HEIGHT, WIDTH), dtype=np.bool_)},
            r"a mask, but its task is object detection",
            id="mask-of-detection-model",
        ),
    ],
)
def test_check_predictions__invalid_object_detection(fields: dict[str, Any], message: str) -> None:
    prediction = _make_prediction(fields=fields)

    with pytest.raises(ProviderError, match=message):
        predicted_annotation_checks.check_predictions(
            predictions=[prediction],
            task=ModelTask.OBJECT_DETECTION,
            class_names=["cat"],
            width=WIDTH,
            height=HEIGHT,
        )


@pytest.mark.parametrize(
    ("fields", "message"),
    [
        pytest.param(
            {"mask": None}, r"no mask, but its task is instance segmentation", id="mask-missing"
        ),
        pytest.param(
            {"mask": [[True] * WIDTH] * HEIGHT}, r"a mask that is not a NumPy array", id="mask-list"
        ),
        pytest.param(
            {"mask": np.ones((WIDTH, HEIGHT), dtype=np.bool_)},
            r"a mask that does not have the shape \(2, 4\)",
            id="mask-shape",
        ),
        pytest.param(
            {"mask": np.ones((HEIGHT, WIDTH), dtype=np.float32)},
            r"a mask that is not of dtype bool",
            id="mask-dtype",
        ),
        # The box of a mask prediction is not used, but it must be valid.
        pytest.param(
            {"mask": np.ones((HEIGHT, WIDTH), dtype=np.bool_), "box": (3.0, 0.0, 1.0, 2.0)},
            r"a positive size",
            id="box-inverted-with-mask",
        ),
    ],
)
def test_check_predictions__invalid_instance_segmentation(
    fields: dict[str, Any], message: str
) -> None:
    prediction = _make_prediction(fields=fields)

    with pytest.raises(ProviderError, match=message):
        predicted_annotation_checks.check_predictions(
            predictions=[prediction],
            task=ModelTask.INSTANCE_SEGMENTATION,
            class_names=["cat"],
            width=WIDTH,
            height=HEIGHT,
        )


@pytest.mark.parametrize(
    "predictions",
    [
        pytest.param(None, id="none"),
        pytest.param([{"class_name": "cat", "box": FULL_BOX, "score": 0.8}], id="dict"),
    ],
)
def test_check_predictions__not_predicted_annotations(predictions: Any) -> None:
    with pytest.raises(ProviderError, match=r"not a list of PredictedAnnotation"):
        predicted_annotation_checks.check_predictions(
            predictions=predictions,
            task=ModelTask.OBJECT_DETECTION,
            class_names=["cat"],
            width=WIDTH,
            height=HEIGHT,
        )


@pytest.mark.parametrize(
    ("task", "fields"),
    [
        pytest.param(ModelTask.OBJECT_DETECTION, {"class_name": "secret"}, id="class-name"),
        pytest.param(ModelTask.OBJECT_DETECTION, {"score": 7.25}, id="score"),
        pytest.param(ModelTask.OBJECT_DETECTION, {"box": (7.25, 0.0, 1.0, 2.0)}, id="box"),
        pytest.param(
            ModelTask.INSTANCE_SEGMENTATION,
            {"mask": np.ones((7, 25), dtype=np.bool_)},
            id="mask-shape",
        ),
        # A structured dtype prints the names of its fields.
        pytest.param(
            ModelTask.INSTANCE_SEGMENTATION,
            {"mask": np.zeros((HEIGHT, WIDTH), dtype=[("secret", "i4")])},
            id="mask-structured-dtype",
        ),
    ],
)
def test_check_predictions__message_omits_value__log_has_value(
    task: ModelTask, fields: dict[str, Any], caplog: pytest.LogCaptureFixture
) -> None:
    prediction = _make_prediction(fields=fields)

    with caplog.at_level(logging.WARNING), pytest.raises(ProviderError) as error_info:
        predicted_annotation_checks.check_predictions(
            predictions=[prediction],
            task=task,
            class_names=["cat"],
            width=WIDTH,
            height=HEIGHT,
        )

    message = str(error_info.value)
    assert "secret" not in message
    assert "7" not in message
    assert "See the server log." in message
    assert "secret" in caplog.text or "7" in caplog.text


def _make_prediction(fields: dict[str, Any]) -> PredictedAnnotation:
    """Returns a valid box prediction of the class "cat" with the fields replaced."""
    return PredictedAnnotation(**{"class_name": "cat", "box": FULL_BOX, "score": 0.8, **fields})
