"""DB-aware runner for object detection evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import aliased
from sqlmodel import Session, col, select

from lightly_studio.evaluation import common, object_detection
from lightly_studio.evaluation.object_detection import BoundingBox, ImageMatchingResult
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
from lightly_studio.models.sample import SampleTable


@dataclass
class EvaluationConfig:
    """Configuration for an object detection evaluation run.

    Attributes:
        iou_threshold: Minimum IoU for a prediction to count as a TP.
        classwise: If True, predictions and ground truths are only matched within
            the same class. If False, matching is done globally across all classes.
    """

    iou_threshold: float
    classwise: bool = True

@dataclass
class SampleMetrics:
    """Configuration for an object detection evaluation run.

    Attributes:
        iou_threshold: Minimum IoU for a prediction to count as a TP.
        classwise: If True, predictions and ground truths are only matched within
            the same class. If False, matching is done globally across all classes.
    """
    sample_id: UUID
    tp: int
    fp: int
    fn: int


def run(
    session: Session,
    gt_collection_id: UUID,
    prediction_collection_id: UUID,
    sample_ids: set[UUID],
    config: EvaluationConfig,
) -> common.EvaluationRunResult:
    """Run object detection evaluation for a set of samples.

    For each sample, ground truth and predicted annotations are loaded from
    their respective collections, matched per sample, and returned as per-sample
    TP/FP/FN results.

    Args:
        session: Database session.
        gt_collection_id: Collection containing the ground truth annotations.
        prediction_collection_id: Collection containing the predicted annotations.
        sample_ids: Parent sample IDs to evaluate.
        config: Evaluation configuration.

    Returns:
        Evaluation results with per-sample TP/FP/FN counts.
    """
    per_sample = [
        _match_image(
            session=session,
            sample_id=sample_id,
            gt_collection_id=gt_collection_id,
            prediction_collection_id=prediction_collection_id,
            config=config,
        )
        for sample_id in sample_ids
    ]
    return common.EvaluationRunResult(per_sample=per_sample)


def _match_image(
    session: Session,
    sample_id: UUID,
    gt_collection_id: UUID,
    prediction_collection_id: UUID,
    *,
    config: EvaluationConfig,
) -> ImageMatchingResult:
    ground_truths = _to_bounding_boxes(
        _load_sample_od_annotations(
            session=session, sample_id=sample_id, collection_id=gt_collection_id
        )
    )
    predictions = _to_bounding_boxes(
        _load_sample_od_annotations(
            session=session, sample_id=sample_id, collection_id=prediction_collection_id
        )
    )
    result = object_detection.match_image(
        sample_id=sample_id,
        predictions=predictions,
        ground_truths=ground_truths,
        iou_threshold=config.iou_threshold,
        classwise=config.classwise,
    )

    return SampleMetrics(sample_id=sample_id, tp=result.tp, fp=result.fp, fn=result.fn)


def _load_sample_od_annotations(
    session: Session,
    sample_id: UUID,
    collection_id: UUID,
) -> list[AnnotationBaseTable]:
    annotation_sample = aliased(SampleTable)
    stmt = (
        select(AnnotationBaseTable)
        .join(annotation_sample, AnnotationBaseTable.sample)
        .where(col(AnnotationBaseTable.parent_sample_id) == sample_id)
        .where(col(annotation_sample.collection_id) == collection_id)
        .where(col(AnnotationBaseTable.annotation_type) == AnnotationType.OBJECT_DETECTION)
    )
    return list(session.exec(stmt).all())


def _to_bounding_boxes(annotations: list[AnnotationBaseTable]) -> list[BoundingBox]:
    boxes = []
    for ann in annotations:
        if ann.object_detection_details is None:
            continue
        boxes.append(
            BoundingBox(
                uuid=ann.sample_id,
                x=ann.object_detection_details.x,
                y=ann.object_detection_details.y,
                width=ann.object_detection_details.width,
                height=ann.object_detection_details.height,
                label=ann.annotation_label_id,
                confidence=ann.confidence,
            )
        )
    return boxes
