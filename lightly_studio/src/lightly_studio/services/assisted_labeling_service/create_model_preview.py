"""Previews of the annotations that a model predicts."""

from __future__ import annotations

import math

import numpy as np

from lightly_studio.assisted_labeling.labeling_model import (
    LabelingModel,
    PredictedAnnotation,
)
from lightly_studio.assisted_labeling.provider import BoxPrompt, ProviderError, ProviderImage
from lightly_studio.core.annotation import annotation_create
from lightly_studio.models.assisted_labeling import (
    AnnotationPreviewBox,
    ModelAnnotationPreview,
    ModelAnnotationRequest,
    ModelAnnotationResponse,
)
from lightly_studio.services.assisted_labeling_service import run_provider


def create_model_preview(
    model: LabelingModel,
    image: ProviderImage,
    request: ModelAnnotationRequest,
    user_email: str | None,
) -> ModelAnnotationResponse:
    """Returns the previews of the predicted annotations sorted by score. Saves nothing.

    Drops the predictions with a score below `request.threshold`, with a class outside
    `request.class_names`, or with an empty mask. The number of previews is limited by
    `request.max_instances`.

    Args:
        model: The model to run.
        image: The image to label.
        request: The preview request.
        user_email: Email of the user who triggered the call, if known.

    Raises:
        ProviderUnavailableError: If the model is not configured.
        ProviderError: If the model fails or returns an invalid prediction.
    """
    predictions = run_provider.predict(
        model=model,
        image=image,
        threshold=request.threshold,
        collection_id=request.collection_id,
        user_email=user_email,
    )
    class_names = None if request.class_names is None else set(request.class_names)
    previews = []
    for prediction in predictions:
        # A model can ignore the threshold
        if prediction.score < request.threshold:
            continue
        if class_names is not None and prediction.class_name not in class_names:
            continue
        preview = _to_model_preview(prediction=prediction, width=image.width, height=image.height)
        if preview is not None:
            previews.append(preview)
    previews.sort(key=lambda preview: -preview.score)
    return ModelAnnotationResponse(predictions=previews[: request.max_instances])


def _to_model_preview(
    prediction: PredictedAnnotation, width: int, height: int
) -> ModelAnnotationPreview | None:
    """Returns the preview of a prediction, or None if its mask is empty.

    A mask defines the box, because the box of the model can differ from the mask.

    Raises:
        ProviderError: If the box is not finite or the mask has the wrong shape.
    """
    if prediction.mask is None:
        box = _to_box_prompt(box=prediction.box, width=width, height=height)
        return ModelAnnotationPreview(
            class_name=prediction.class_name,
            bbox=AnnotationPreviewBox(
                x=box.x_min, y=box.y_min, width=box.x_max - box.x_min, height=box.y_max - box.y_min
            ),
            segmentation_mask=None,
            score=prediction.score,
        )
    if prediction.mask.shape != (height, width):
        raise ProviderError(
            f"The model returned a mask of shape {prediction.mask.shape}, "
            f"expected ({height}, {width})."
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


def _to_box_prompt(box: tuple[float, float, float, float], width: int, height: int) -> BoxPrompt:
    """Returns the integer box that contains the float box, clamped to the image.

    Raises:
        ProviderError: If a box value is not finite.
    """
    x_min, y_min, x_max, y_max = box
    if not all(math.isfinite(value) for value in box):
        raise ProviderError(f"The model returned a box with a value that is not finite: {box}.")
    left = min(max(math.floor(x_min), 0), width - 1)
    top = min(max(math.floor(y_min), 0), height - 1)
    return BoxPrompt(
        x_min=left,
        y_min=top,
        x_max=min(max(math.ceil(x_max), left + 1), width),
        y_max=min(max(math.ceil(y_max), top + 1), height),
    )
