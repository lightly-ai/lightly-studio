"""Previews of the annotations that a labeling model predicts."""

from __future__ import annotations

import logging
import math
from collections.abc import Set

import numpy as np
from lightly_studio_serve.labeling import PredictedAnnotation

from lightly_studio.assisted_labeling.labeling_model_runner import LabelingModelRunner
from lightly_studio.assisted_labeling.provider import ProviderError, ProviderImage
from lightly_studio.core.annotation import annotation_create
from lightly_studio.models.assisted_labeling import (
    MAX_MODEL_PREVIEWS,
    AnnotationPreviewBox,
    ModelAnnotationPreview,
    ModelAnnotationRequest,
    ModelAnnotationResponse,
)

logger = logging.getLogger(__name__)


def create_model_preview(
    runner: LabelingModelRunner,
    image: ProviderImage,
    request: ModelAnnotationRequest,
) -> ModelAnnotationResponse:
    """Returns the previews of the predicted annotations sorted by score. Saves nothing.

    Drops the predictions with a score below `request.threshold`, with an empty mask, or
    with a box that is fully outside the image.
    Returns at most `MAX_MODEL_PREVIEWS` previews.

    Args:
        runner: The runner of the labeling model.
        image: The image to label.
        request: The preview request.

    Raises:
        NotFoundError: If the image file cannot be read.
        ProviderError: If the model fails or returns a prediction that is not valid.
    """
    predictions = runner.predict(image=image, threshold=request.threshold)
    class_names = frozenset(runner.class_names)
    for prediction in predictions:
        _check_prediction(
            prediction=prediction, class_names=class_names, width=image.width, height=image.height
        )
    # A model can ignore the threshold
    candidates = [prediction for prediction in predictions if prediction.score >= request.threshold]
    candidates.sort(key=lambda prediction: -prediction.score)
    previews: list[ModelAnnotationPreview] = []
    for prediction in candidates:
        # The conversion of a mask is slow, so the loop converts only the returned previews
        if len(previews) == MAX_MODEL_PREVIEWS:
            break
        preview = _to_model_preview(prediction=prediction, width=image.width, height=image.height)
        if preview is not None:
            previews.append(preview)
    return ModelAnnotationResponse(predictions=previews)


def _check_prediction(
    prediction: PredictedAnnotation, class_names: Set[str], width: int, height: int
) -> None:
    """Refuse a prediction that LightlyStudio cannot show or save.

    Args:
        prediction: The prediction of the model.
        class_names: The annotation classes that the model declares.
        width: Image width in pixels.
        height: Image height in pixels.

    Raises:
        ProviderError: If the prediction is not valid. The message names the field. It
            does not hold the class name, because API callers see the message.
    """
    score = prediction.score
    # A NaN fails the range check too
    if not 0 <= score <= 1:
        raise ProviderError(f"The model returned the score {score}, expected a value from 0 to 1.")
    if prediction.class_name not in class_names:
        logger.warning(
            "A labeling model returned the class %r, which is not one of its class names.",
            prediction.class_name,
        )
        raise ProviderError(
            "The model returned a class that is not one of its class names. See the server log."
        )
    x_min, y_min, x_max, y_max = prediction.box
    if not all(math.isfinite(value) for value in prediction.box):
        raise ProviderError(
            f"The model returned a box with a value that is not finite: {prediction.box}."
        )
    if x_min >= x_max or y_min >= y_max:
        raise ProviderError(
            f"The model returned the box {prediction.box}, "
            "expected (x_min, y_min, x_max, y_max) with a positive size."
        )
    mask = prediction.mask
    if mask is None:
        return
    if mask.shape != (height, width):
        raise ProviderError(
            f"The model returned a mask of shape {mask.shape}, expected ({height}, {width})."
        )
    if mask.dtype != np.bool_:
        raise ProviderError(f"The model returned a mask of dtype {mask.dtype}, expected bool.")


def _to_model_preview(
    prediction: PredictedAnnotation, width: int, height: int
) -> ModelAnnotationPreview | None:
    """Returns the preview of a valid prediction.

    Returns None if the mask is empty, or if the prediction has no mask and its box is
    fully outside the image. A mask defines the box, because the box of the model can
    differ from the mask.
    """
    if prediction.mask is None:
        if _is_outside_image(box=prediction.box, width=width, height=height):
            return None
        return ModelAnnotationPreview(
            class_name=prediction.class_name,
            bbox=_to_preview_box(box=prediction.box, width=width, height=height),
            segmentation_mask=None,
            score=prediction.score,
        )
    if not np.any(prediction.mask):
        return None
    segmentation_mask, (x, y, box_width, box_height) = (
        annotation_create.segmentation_mask_and_bounding_box(
            binary_mask=prediction.mask.astype(np.int_)
        )
    )
    return ModelAnnotationPreview(
        class_name=prediction.class_name,
        bbox=AnnotationPreviewBox(x=x, y=y, width=box_width, height=box_height),
        segmentation_mask=segmentation_mask,
        score=prediction.score,
    )


def _to_preview_box(
    box: tuple[float, float, float, float], width: int, height: int
) -> AnnotationPreviewBox:
    """Returns the integer box that contains the float box, clamped to the image.

    The box has at least one pixel in each direction.
    """
    x_min, y_min, x_max, y_max = box
    left = min(max(math.floor(x_min), 0), width - 1)
    top = min(max(math.floor(y_min), 0), height - 1)
    right = min(max(math.ceil(x_max), left + 1), width)
    bottom = min(max(math.ceil(y_max), top + 1), height)
    return AnnotationPreviewBox(x=left, y=top, width=right - left, height=bottom - top)


def _is_outside_image(box: tuple[float, float, float, float], width: int, height: int) -> bool:
    """Returns True if no part of the box is inside the image.

    A box that only touches an edge of the image is outside.

    Args:
        box: A finite box `(x_min, y_min, x_max, y_max)` in pixels with a positive size.
        width: Image width in pixels.
        height: Image height in pixels.
    """
    x_min, y_min, x_max, y_max = box
    return x_max <= 0 or y_max <= 0 or x_min >= width or y_min >= height
