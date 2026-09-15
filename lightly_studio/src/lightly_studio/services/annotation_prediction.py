"""Convert full-image model geometry to Studio annotation inputs."""

from __future__ import annotations

import math

import numpy as np
from labelformat.model.binary_mask_segmentation import BinaryMaskSegmentation
from labelformat.model.bounding_box import BoundingBox

from lightly_studio.core.annotation.annotation_create import (
    CreateObjectDetection,
    CreateSegmentationMask,
)
from lightly_studio.models.auto_labeling import BoxPrediction, MaskPrediction, Prediction, Task
from lightly_studio.models.image import ImageTable


def convert_prediction(
    prediction: Prediction, image: ImageTable, task: Task
) -> CreateObjectDetection | CreateSegmentationMask | None:
    """Convert supported geometry, ignoring other annotation kinds."""
    if isinstance(prediction, MaskPrediction):
        mask = convert_mask(prediction=prediction, image=image)
        if mask is None or task == "segmentation":
            return mask
        return CreateObjectDetection(**mask.model_dump(exclude={"segmentation_mask"}))
    if isinstance(prediction, BoxPrediction) and task == "object_detection":
        x, y, width, height = prediction.bbox
        left, top = math.floor(x * image.width), math.floor(y * image.height)
        right = min(image.width, math.ceil((x + width) * image.width))
        bottom = min(image.height, math.ceil((y + height) * image.height))
        return CreateObjectDetection(
            class_name=prediction.class_name,
            confidence=prediction.score,
            x=left,
            y=top,
            width=right - left,
            height=bottom - top,
        )
    return None


def convert_mask(
    prediction: MaskPrediction, image: ImageTable, crop_to_bbox: bool = False
) -> CreateSegmentationMask | None:
    """Decode row-major runs and crop with the existing annotation conversion."""
    if (prediction.image_width, prediction.image_height) != (image.width, image.height):
        raise ValueError("The annotation model mask dimensions do not match the original image.")
    if not sum(prediction.rle[1::2]):
        return None
    values = np.arange(len(prediction.rle), dtype=np.int_) % 2
    binary_mask = np.repeat(values, prediction.rle).reshape(image.height, image.width)
    rows, columns = np.where(binary_mask)
    x, y = int(columns.min()), int(rows.min())
    width = int(columns.max() - x + 1)
    height = int(rows.max() - y + 1)
    if not crop_to_bbox:
        return CreateSegmentationMask.from_binary_mask(
            class_name=prediction.class_name,
            confidence=prediction.score,
            binary_mask=binary_mask,
        )

    cropped_mask = binary_mask[y : y + height, x : x + width]
    segmentation_mask = BinaryMaskSegmentation.from_binary_mask(
        binary_mask=cropped_mask,
        bounding_box=BoundingBox(xmin=0, ymin=0, xmax=width, ymax=height),
    ).get_rle()
    return CreateSegmentationMask(
        class_name=prediction.class_name,
        confidence=prediction.score,
        x=x,
        y=y,
        width=width,
        height=height,
        segmentation_mask=segmentation_mask,
    )
