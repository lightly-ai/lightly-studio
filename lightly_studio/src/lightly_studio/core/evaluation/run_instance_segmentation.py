"""Instance-segmentation evaluation runner."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.core.evaluation import (
    common,
    compute_instance_segmentation_metrics,
    load_annotations,
)


def run(  # noqa: PLR0913
    session: Session,
    gt_collection_id: UUID,
    prediction_collection_id: UUID,
    sample_ids: set[UUID],
    iou_threshold: float,
    confidence_threshold: float,
) -> common.EvaluationRunResult:
    """Run instance-segmentation evaluation for one GT/prediction pair."""
    gt_annotations = load_annotations.load_instance_segmentation_annotations(
        session,
        gt_collection_id,
        sample_ids=sample_ids,
    )
    pred_annotations = load_annotations.load_instance_segmentation_annotations(
        session,
        prediction_collection_id,
        sample_ids=sample_ids,
    )

    label_names = load_annotations.load_label_names_for_annotations(
        session, gt_annotations, pred_annotations
    )

    match_records = compute_instance_segmentation_metrics.match_annotations(
        gt_annotations,
        pred_annotations,
        iou_threshold,
        confidence_threshold,
    )
    pred_confidences = {
        annotation.annotation_id: annotation.confidence for annotation in pred_annotations
    }

    metrics: dict[str, object] = {
        "all": compute_instance_segmentation_metrics.compute_metrics(
            match_records, pred_confidences, label_names
        )
    }
    return common.EvaluationRunResult(metrics=metrics, match_records=match_records)
