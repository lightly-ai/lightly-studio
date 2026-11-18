"""Previews of the annotations that a labeling model predicts."""

from __future__ import annotations

import math

from lightly_studio_serve.labeling import PredictedAnnotation

from lightly_studio.assisted_labeling import predicted_annotation_checks
from lightly_studio.assisted_labeling.labeling_model_runner import LabelingModelRunner
from lightly_studio.assisted_labeling.provider import ProviderImage
from lightly_studio.models.assisted_labeling import (
    MAX_MODEL_PREVIEWS,
    AnnotationPreviewBox,
    ModelAnnotationPreview,
    ModelAnnotationResponse,
)
from lightly_studio.services.assisted_labeling_service import to_annotation_preview


def create_model_preview(
    runner: LabelingModelRunner,
    image: ProviderImage,
    threshold: float,
) -> ModelAnnotationResponse:
    """Returns the previews of the predicted annotations sorted by score. Saves nothing.

    Drops the predictions with a score below `threshold`, with an empty mask, or with a
    box that is fully outside the image.
    Returns at most `MAX_MODEL_PREVIEWS` previews.

    Args:
        runner: The runner of the labeling model.
        image: The image to label.
        threshold: Minimum confidence score of a preview, from 0 to 1.

    Raises:
        NotFoundError: If the image file cannot be read.
        ProviderError: If the model fails, or if one prediction is not valid. A
            prediction below `threshold` that is not valid fails the request too.
    """
    predictions = runner.predict(image=image, threshold=threshold)
    predicted_annotation_checks.check_predictions(
        predictions=predictions,
        task=runner.task,
        class_names=runner.class_names,
        width=image.width,
        height=image.height,
    )
    # A model can ignore the threshold
    candidates = [prediction for prediction in predictions if prediction.score >= threshold]
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
    encoded_mask = to_annotation_preview.encode_mask(mask=prediction.mask)
    if encoded_mask is None:
        return None
    segmentation_mask, bbox = encoded_mask
    return ModelAnnotationPreview(
        class_name=prediction.class_name,
        bbox=bbox,
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
