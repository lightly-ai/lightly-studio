"""Semantic segmentation evaluation metric primitives."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

import numpy as np
from labelformat.model.binary_mask_segmentation import BinaryMaskSegmentation
from labelformat.model.bounding_box import BoundingBox
from numpy.typing import NDArray
from sqlmodel import Session

from lightly_studio.evaluation.evaluation_data import EvaluationData
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.evaluation_sample_metric import EvaluationSampleMetricCreate
from lightly_studio.models.image import ImageTable
from lightly_studio.resolvers import evaluation_sample_metric_resolver, image_resolver

METRIC_BATCH_SIZE = 32  # Buffer size for evaluation_sample_metric_resolver.create_many
_MIOU_METRIC_NAME = "miou"


def create_and_persist_semantic_segmentation_metrics_per_sample(
    session: Session,
    data: EvaluationData,
) -> None:
    """Create and persist per-sample semantic-segmentation metrics.

    For each selected sample, decodes GT and prediction segmentation masks at
    pixel level (ignoring bounding-box geometry except for mask placement),
    computes per-annotation-class IoU, and writes ``miou``: mean IoU over all
    classes present in GT or predictions on that image, with equal weight per
    class.

    Raises:
        ValueError: If a sample has no image dimensions or no class masks to score.
    """
    images = image_resolver.get_many_by_id(session=session, sample_ids=data.selected_sample_ids)
    image_by_sample_id = {image.sample_id: image for image in images}

    metrics_to_persist: list[EvaluationSampleMetricCreate] = []
    for sample_id in data.selected_sample_ids:
        image = image_by_sample_id.get(sample_id)
        if image is None:
            raise ValueError(
                f"Semantic segmentation evaluation expected image dimensions for "
                f"sample {sample_id}, but no image was found."
            )

        gt_masks = _class_masks_from_annotations(
            annotations=data.gt_per_sample.get(sample_id, []),
            image=image,
        )
        pred_masks = _class_masks_from_annotations(
            annotations=data.pred_per_sample.get(sample_id, []),
            image=image,
        )
        class_ious = compute_class_ious(gt_masks=gt_masks, pred_masks=pred_masks)
        if not class_ious:
            raise ValueError(
                f"Semantic segmentation evaluation expected at least one class mask "
                f"for sample {sample_id}, but none were found."
            )

        metrics_to_persist.append(
            _sample_metric_record(
                evaluation_run_id=data.evaluation_run_id,
                sample_id=sample_id,
                class_ious=class_ious,
            )
        )

        if len(metrics_to_persist) >= METRIC_BATCH_SIZE:
            evaluation_sample_metric_resolver.create_many(
                session=session,
                records=metrics_to_persist,
            )
            metrics_to_persist.clear()

    if metrics_to_persist:
        evaluation_sample_metric_resolver.create_many(
            session=session,
            records=metrics_to_persist,
        )


def compute_class_ious(
    gt_masks: dict[UUID, NDArray[np.bool_]],
    pred_masks: dict[UUID, NDArray[np.bool_]],
) -> dict[UUID, float]:
    """Compute per-class IoU from accumulated binary masks.

    Classes included are those with at least one foreground pixel in GT or
    predictions. Each class has equal weight when aggregating to mIoU.

    Args:
        gt_masks: Ground-truth binary masks keyed by annotation label id.
        pred_masks: Prediction binary masks keyed by annotation label id.

    Returns:
        Mapping from annotation label id to IoU in ``[0, 1]``.
    """
    class_ids = {
        label_id
        for label_id in gt_masks | pred_masks
        if gt_masks.get(label_id, _empty_mask(gt_masks, pred_masks)).any()
        or pred_masks.get(label_id, _empty_mask(gt_masks, pred_masks)).any()
    }
    if not class_ids:
        return {}

    empty_mask = _empty_mask(gt_masks, pred_masks)
    return {
        label_id: compute_iou(
            gt_mask=gt_masks.get(label_id, empty_mask),
            pred_mask=pred_masks.get(label_id, empty_mask),
        )
        for label_id in class_ids
    }


def compute_iou(
    gt_mask: NDArray[np.bool_],
    pred_mask: NDArray[np.bool_],
) -> float:
    """Compute intersection-over-union for two binary masks of the same shape."""
    if gt_mask.shape != pred_mask.shape:
        raise ValueError(
            f"GT mask shape {gt_mask.shape} does not match prediction mask shape {pred_mask.shape}."
        )
    intersection = float(np.logical_and(gt_mask, pred_mask).sum())
    union = float(np.logical_or(gt_mask, pred_mask).sum())
    if union == 0.0:
        return 1.0
    return intersection / union


def _class_masks_from_annotations(
    annotations: Sequence[AnnotationBaseTable],
    image: ImageTable,
) -> dict[UUID, NDArray[np.bool_]]:
    """Decode segmentation annotations into per-class binary masks."""
    masks: dict[UUID, NDArray[np.bool_]] = {}
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

        class_mask = masks.setdefault(
            annotation.annotation_label_id,
            np.zeros((image.height, image.width), dtype=np.bool_),
        )
        class_mask |= binary_mask.astype(np.bool_)
    return masks


def _sample_metric_record(
    evaluation_run_id: UUID,
    sample_id: UUID,
    class_ious: dict[UUID, float],
) -> EvaluationSampleMetricCreate:
    """Build the sample-level mIoU metric row."""
    return EvaluationSampleMetricCreate(
        evaluation_run_id=evaluation_run_id,
        sample_id=sample_id,
        metric_name=_MIOU_METRIC_NAME,
        value=float(np.mean(list(class_ious.values()))),
    )


def _empty_mask(
    gt_masks: dict[UUID, NDArray[np.bool_]],
    pred_masks: dict[UUID, NDArray[np.bool_]],
) -> NDArray[np.bool_]:
    for masks in (gt_masks, pred_masks):
        if masks:
            reference = next(iter(masks.values()))
            return np.zeros(reference.shape, dtype=np.bool_)
    return np.zeros((0, 0), dtype=np.bool_)
