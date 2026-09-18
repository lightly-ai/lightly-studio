"""Instance segmentation evaluation metric primitives.

Instance segmentation is matched exactly like object detection, but the greedy
matcher runs on mask IoU instead of box IoU. The matcher and the metric-record
builders are therefore reused from ``object_detection_metric``.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

import numpy as np
from labelformat.model.binary_mask_segmentation import BinaryMaskSegmentation
from labelformat.model.bounding_box import BoundingBox
from numpy.typing import NDArray
from sqlmodel import Session

from lightly_studio.evaluation.evaluation_data import EvaluationData
from lightly_studio.evaluation.object_detection_metric import (
    MatchingResult,
    get_annotation_metric_records,
    get_sample_metric_records,
    match_with_iou_matrix,
)
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.evaluation_annotation_metric import EvaluationAnnotationMetricCreate
from lightly_studio.models.evaluation_sample_metric import EvaluationSampleMetricCreate
from lightly_studio.models.image import ImageTable
from lightly_studio.resolvers import (
    evaluation_annotation_metric_resolver,
    evaluation_sample_metric_resolver,
    image_resolver,
)

METRIC_BATCH_SIZE = 32  # Buffer size for evaluation_sample_metric_resolver.create_many


@dataclass
class InstanceMask:
    """A single instance-segmentation mask, ready for greedy matching.

    Attributes:
        annotation_id: Unique identifier, used to map results back to source annotations.
        mask: Binary mask of shape (H, W), the image height and width.
        label_id: Class label ID.
        confidence: Prediction confidence score. None for ground truth annotations.
    """

    annotation_id: UUID
    mask: NDArray[np.bool_]
    label_id: UUID
    confidence: float | None = None


def compute_mask_iou_matrix(
    pred_masks: Sequence[NDArray[np.bool_]],
    gt_masks: Sequence[NDArray[np.bool_]],
) -> NDArray[np.float64]:
    """Compute pairwise mask IoU.

    P is the number of predicted masks, G the number of ground truth masks, and H and W
    the mask height and width.

    Args:
        pred_masks: Predicted binary masks, each of shape (H, W).
        gt_masks: Ground truth binary masks, each of shape (H, W).

    Returns:
        IoU matrix of shape (P, G). An empty mask pair (union of zero pixels) has an
        IoU of 0.
    """
    pred_areas = [float(mask.sum()) for mask in pred_masks]
    gt_areas = [float(mask.sum()) for mask in gt_masks]
    iou_matrix = np.zeros((len(pred_masks), len(gt_masks)), dtype=np.float64)
    for pred_idx, pred_mask in enumerate(pred_masks):
        for gt_idx, gt_mask in enumerate(gt_masks):
            intersection = float(np.logical_and(pred_mask, gt_mask).sum())
            union = pred_areas[pred_idx] + gt_areas[gt_idx] - intersection
            if union > 0.0:
                iou_matrix[pred_idx, gt_idx] = intersection / union
    return iou_matrix


def match_image(
    predictions: Sequence[InstanceMask],
    ground_truths: Sequence[InstanceMask],
    iou_threshold: float,
    classwise: bool,
) -> MatchingResult:
    """Match predicted instance masks to ground truths for a single image.

    Uses mask IoU with the same greedy matcher as object detection.

    Args:
        predictions: All predicted instance masks for the image.
        ground_truths: All ground truth instance masks for the image.
        iou_threshold: Minimum mask IoU for a prediction to count as a TP.
        classwise: If True, predictions and ground truths are only matched within
            the same class. If False, matching is done globally across all classes.

    Returns:
        Per-image matching result.
    """
    if classwise:
        all_labels = {m.label_id for m in predictions} | {m.label_id for m in ground_truths}
        result = MatchingResult()
        for label in all_labels:
            class_predictions = [m for m in predictions if m.label_id == label]
            class_gts = [m for m in ground_truths if m.label_id == label]
            result.extend(
                match_with_iou_matrix(
                    predictions=class_predictions,
                    ground_truths=class_gts,
                    iou_matrix=compute_mask_iou_matrix(
                        pred_masks=[m.mask for m in class_predictions],
                        gt_masks=[m.mask for m in class_gts],
                    ),
                    iou_threshold=iou_threshold,
                )
            )
        return result
    return match_with_iou_matrix(
        predictions=predictions,
        ground_truths=ground_truths,
        iou_matrix=compute_mask_iou_matrix(
            pred_masks=[m.mask for m in predictions],
            gt_masks=[m.mask for m in ground_truths],
        ),
        iou_threshold=iou_threshold,
    )


def create_and_persist_instance_segmentation_metrics_per_sample(
    session: Session,
    data: EvaluationData,
    iou_threshold: float,
    classwise: bool,
) -> None:
    """Create and persist per-sample instance-segmentation metrics.

    For each selected sample, decodes GT and prediction instance masks, matches
    them by mask IoU, and writes per-sample ``tp``/``fp``/``fn`` and per-match
    ``iou`` metrics, mirroring object detection.

    Raises:
        ValueError: If a sample has no image to decode masks with, or if a
            decoded mask does not match the image dimensions.
    """
    images = image_resolver.get_many_by_id(
        session=session,
        sample_ids=list(data.selected_sample_ids),
    )
    image_by_sample_id = {image.sample_id: image for image in images}

    sample_metrics_to_persist: list[EvaluationSampleMetricCreate] = []
    annotation_metrics_to_persist: list[EvaluationAnnotationMetricCreate] = []

    for sample_id in data.selected_sample_ids:
        image = image_by_sample_id.get(sample_id)
        if image is None:
            raise ValueError(
                f"Instance segmentation evaluation expected image dimensions for "
                f"sample {sample_id}, but no image was found."
            )

        matching_result = match_image(
            predictions=_to_instance_masks(
                annotations=data.pred_per_sample.get(sample_id, []), image=image
            ),
            ground_truths=_to_instance_masks(
                annotations=data.gt_per_sample.get(sample_id, []), image=image
            ),
            iou_threshold=iou_threshold,
            classwise=classwise,
        )

        sample_metrics_to_persist.extend(
            get_sample_metric_records(
                evaluation_run_id=data.evaluation_run_id,
                sample_id=sample_id,
                matching_result=matching_result,
            )
        )
        annotation_metrics_to_persist.extend(
            get_annotation_metric_records(
                evaluation_run_id=data.evaluation_run_id,
                sample_id=sample_id,
                matching_result=matching_result,
            )
        )
        if len(sample_metrics_to_persist) >= METRIC_BATCH_SIZE:
            evaluation_sample_metric_resolver.create_many(
                session=session,
                records=sample_metrics_to_persist,
            )
            sample_metrics_to_persist.clear()
        if len(annotation_metrics_to_persist) >= METRIC_BATCH_SIZE:
            evaluation_annotation_metric_resolver.create_many(
                session=session,
                records=annotation_metrics_to_persist,
            )
            annotation_metrics_to_persist.clear()

    if sample_metrics_to_persist:
        evaluation_sample_metric_resolver.create_many(
            session=session,
            records=sample_metrics_to_persist,
        )
    if annotation_metrics_to_persist:
        evaluation_annotation_metric_resolver.create_many(
            session=session,
            records=annotation_metrics_to_persist,
        )


def _to_instance_masks(
    annotations: Sequence[AnnotationBaseTable],
    image: ImageTable,
) -> list[InstanceMask]:
    """Decode instance-segmentation annotations into matcher-ready masks."""
    masks: list[InstanceMask] = []
    for annotation in annotations:
        details = annotation.segmentation_details
        if details is None or details.segmentation_mask is None:
            continue
        binary_mask = BinaryMaskSegmentation.from_rle(
            rle_row_wise=details.segmentation_mask,
            width=image.width,
            height=image.height,
            bounding_box=BoundingBox(
                xmin=details.x,
                ymin=details.y,
                xmax=details.x + details.width,
                ymax=details.y + details.height,
            ),
        ).get_binary_mask()
        if binary_mask.shape != (image.height, image.width):
            raise ValueError(
                f"Segmentation mask for annotation {annotation.sample_id} has shape "
                f"{binary_mask.shape}, expected {(image.height, image.width)}."
            )
        masks.append(
            InstanceMask(
                annotation_id=annotation.sample_id,
                mask=binary_mask.astype(np.bool_),
                label_id=annotation.annotation_label_id,
                confidence=annotation.confidence,
            )
        )
    return masks
