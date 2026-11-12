"""Previews of the annotations that a labeling model predicts."""

from __future__ import annotations

import math
from collections.abc import Set

import numpy as np
from lightly_studio_serve.types import PredictedAnnotation

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


def create_model_preview(
    runner: LabelingModelRunner,
    image: ProviderImage,
    request: ModelAnnotationRequest,
) -> ModelAnnotationResponse:
    """Returns the previews of the predicted annotations sorted by score. Saves nothing.

    Drops the predictions with a score below `request.threshold` or with an empty mask.
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
    previews = []
    for prediction in predictions:
        _check_prediction(
            prediction=prediction, class_names=class_names, width=image.width, height=image.height
        )
        # A model can ignore the threshold
        if prediction.score < request.threshold:
            continue
        preview = _to_model_preview(prediction=prediction, width=image.width, height=image.height)
        if preview is not None:
            previews.append(preview)
    previews.sort(key=lambda preview: -preview.score)
    return ModelAnnotationResponse(predictions=previews[:MAX_MODEL_PREVIEWS])


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
        ProviderError: If the prediction is not valid. The message names the field.
    """
    score = prediction.score
    # A NaN fails the range check too
    if not 0 <= score <= 1:
        raise ProviderError(f"The model returned the score {score}, expected a value from 0 to 1.")
    if prediction.class_name not in class_names:
        raise ProviderError(
            f"The model returned the class {prediction.class_name!r}, "
            "which is not one of its class names."
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
    """Returns the preview of a valid prediction, or None if its mask is empty.

    A mask defines the box, because the box of the model can differ from the mask.
    """
    if prediction.mask is None:
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
