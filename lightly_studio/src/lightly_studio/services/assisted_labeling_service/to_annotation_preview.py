"""Conversion of provider predictions to annotation previews."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from lightly_studio.assisted_labeling.provider import Prediction, ProviderError
from lightly_studio.core.annotation import annotation_create
from lightly_studio.models.assisted_labeling import AnnotationPreview, AnnotationPreviewBox


def to_sorted_annotation_previews(
    predictions: Sequence[Prediction], width: int, height: int
) -> list[AnnotationPreview]:
    """Returns the previews of the non-empty masks sorted by descending score.

    Predictions without a score come last.

    Args:
        predictions: Provider predictions with full-image masks.
        width: Image width in pixels.
        height: Image height in pixels.

    Raises:
        ProviderError: If a mask shape is not (height, width).
    """
    previews = [
        _to_annotation_preview(prediction=prediction, width=width, height=height)
        for prediction in predictions
    ]
    return sorted(
        (preview for preview in previews if preview is not None),
        key=lambda preview: (preview.score is None, -(preview.score or 0.0)),
    )


def _to_annotation_preview(
    prediction: Prediction, width: int, height: int
) -> AnnotationPreview | None:
    """Returns the preview of a full-image mask, or None if the mask is empty."""
    mask = prediction.mask
    if mask.shape != (height, width):
        raise ProviderError(
            f"The provider returned a mask of shape {mask.shape}, expected ({height}, {width})."
        )
    if not np.any(mask):
        return None
    segmentation_mask, (x, y, box_width, box_height) = (
        annotation_create.segmentation_mask_and_bounding_box(binary_mask=mask.astype(np.int_))
    )
    return AnnotationPreview(
        bbox=AnnotationPreviewBox(x=x, y=y, width=box_width, height=box_height),
        segmentation_mask=segmentation_mask,
        score=prediction.score,
    )
