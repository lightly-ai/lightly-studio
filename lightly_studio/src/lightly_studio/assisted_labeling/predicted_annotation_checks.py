"""Checks of the predictions that a labeling model returns."""

from __future__ import annotations

import logging
import math
from collections.abc import Sequence, Set
from numbers import Real
from typing import NoReturn, TypeGuard

import numpy as np
from lightly_studio_serve.labeling import ModelTask, PredictedAnnotation

from lightly_studio.assisted_labeling.provider import ProviderError

logger = logging.getLogger(__name__)

_BOX_VALUE_COUNT = 4


def check_predictions(
    predictions: Sequence[PredictedAnnotation],
    task: ModelTask,
    class_names: Sequence[str],
    width: int,
    height: int,
) -> None:
    """Checks that LightlyStudio can show and save each prediction of one image.

    A model is user code, so the checks do not trust the types of the fields.

    Args:
        predictions: The predictions, as the model returned them.
        task: The kind of annotations that the model predicts.
        class_names: The annotation classes that the model declares.
        width: Image width in pixels.
        height: Image height in pixels.

    Raises:
        ProviderError: If a prediction is not valid. The message names the field. The
            server log has the value, because API callers see the message.
    """
    is_prediction_list = isinstance(predictions, list) and all(
        isinstance(prediction, PredictedAnnotation) for prediction in predictions
    )
    if not is_prediction_list:
        _refuse(problem="a value that is not a list of PredictedAnnotation", value=predictions)
    declared_class_names = frozenset(class_names)
    for prediction in predictions:
        _check_score(score=prediction.score)
        _check_class_name(class_name=prediction.class_name, class_names=declared_class_names)
        _check_box(box=prediction.box)
        _check_mask_matches_task(mask=prediction.mask, task=task)
        if prediction.mask is not None:
            _check_mask_array(mask=prediction.mask, width=width, height=height)


def _check_score(score: object) -> None:
    """Checks that the score is a number from 0 to 1."""
    # A NaN fails the range check too
    if not _is_number(value=score) or not 0 <= score <= 1:
        _refuse(problem="a score that is not a number from 0 to 1", value=score)


def _check_class_name(class_name: object, class_names: Set[str]) -> None:
    """Checks that the model declares the annotation class."""
    if not isinstance(class_name, str) or class_name not in class_names:
        _refuse(
            problem="an annotation class that is not one of its annotation classes",
            value=class_name,
        )


def _check_box(box: object) -> None:
    """Checks that the box is `(x_min, y_min, x_max, y_max)` with a positive size."""
    if not _is_finite_box(box=box):
        _refuse(problem="a box that is not four finite numbers", value=box)
    x_min, y_min, x_max, y_max = box
    if x_min >= x_max or y_min >= y_max:
        _refuse(problem="a box that does not have a positive size", value=box)


def _check_mask_matches_task(mask: object, task: ModelTask) -> None:
    """Checks that only a model for instance segmentation returns a mask."""
    if task == ModelTask.INSTANCE_SEGMENTATION and mask is None:
        _refuse(problem="no mask, but its task is instance segmentation", value=None)
    if task == ModelTask.OBJECT_DETECTION and mask is not None:
        _refuse(problem="a mask, but its task is object detection", value=type(mask).__name__)


def _check_mask_array(mask: object, width: int, height: int) -> None:
    """Checks that the mask is an array of shape (height, width) and dtype `np.bool_`."""
    if not isinstance(mask, np.ndarray):
        _refuse(problem="a mask that is not a NumPy array", value=type(mask).__name__)
    if mask.shape != (height, width):
        _refuse(
            problem=f"a mask that does not have the shape ({height}, {width}) of the image",
            value=mask.shape,
        )
    if mask.dtype != np.bool_:
        _refuse(problem="a mask that is not of dtype bool", value=mask.dtype)


def _is_finite_box(box: object) -> TypeGuard[Sequence[float]]:
    """Returns True if the box is a tuple or a list of four finite numbers."""
    if not isinstance(box, (tuple, list)) or len(box) != _BOX_VALUE_COUNT:
        return False
    return all(_is_number(value=value) and math.isfinite(value) for value in box)


def _is_number(value: object) -> TypeGuard[float]:
    """Returns True if the value is a real number, for example a NumPy scalar.

    A bool is not a number here, because a bool score or box value is a model bug.
    """
    return isinstance(value, Real) and not isinstance(value, bool)


def _refuse(problem: str, value: object) -> NoReturn:
    """Writes the value to the server log and raises a `ProviderError` without it."""
    logger.warning("A labeling model returned %s: %r", problem, value)
    raise ProviderError(f"The model returned {problem}. See the server log.")
