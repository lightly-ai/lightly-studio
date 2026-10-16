"""Conversion of provider predictions to annotation previews."""

from __future__ import annotations

import numpy as np
from labelformat.model.binary_mask_segmentation import BinaryMaskSegmentation
from labelformat.model.bounding_box import BoundingBox

from lightly_studio.assisted_labeling.provider import Prediction, ProviderError
from lightly_studio.models.assisted_labeling import AnnotationPreview, AnnotationPreviewBox


def to_annotation_preview(
    prediction: Prediction, width: int, height: int
) -> AnnotationPreview | None:
    """Returns the preview of a full-image mask, or None if the mask is empty.

    Raises:
        ProviderError: If the mask shape is not (height, width).
    """
    mask = prediction.mask
    if mask.shape != (height, width):
        raise ProviderError(
            f"The provider returned a mask of shape {mask.shape}, expected ({height}, {width})."
        )
    rows, columns = np.nonzero(mask)
    if rows.size == 0:
        return None
    x, y = int(columns.min()), int(rows.min())
    box_width = int(columns.max()) - x + 1
    box_height = int(rows.max()) - y + 1
    cropped_mask = mask[y : y + box_height, x : x + box_width].astype(np.int_)
    segmentation_mask = BinaryMaskSegmentation.from_binary_mask(
        binary_mask=cropped_mask,
        bounding_box=BoundingBox(xmin=0, ymin=0, xmax=box_width, ymax=box_height),
    ).get_rle()
    return AnnotationPreview(
        bbox=AnnotationPreviewBox(x=x, y=y, width=box_width, height=box_height),
        segmentation_mask=segmentation_mask,
        score=prediction.score,
        class_name=prediction.class_name,
    )


def to_sorted_annotation_previews(
    predictions: list[Prediction], width: int, height: int
) -> list[AnnotationPreview]:
    """Returns the previews of the non-empty masks sorted by descending score.

    Predictions without a score come last.

    Raises:
        ProviderError: If a mask shape is not (height, width).
    """
    previews = [
        to_annotation_preview(prediction=prediction, width=width, height=height)
        for prediction in predictions
    ]
    return sorted(
        (preview for preview in previews if preview is not None),
        key=lambda preview: -1.0 if preview.score is None else preview.score,
        reverse=True,
    )
