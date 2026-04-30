"""Object-detection evaluation runner."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.services.evaluation_service import common, compute_od_metrics, load_annotations


def run(  # noqa: PLR0913
    session: Session,
    gt_collection_id: UUID,
    prediction_collection_id: UUID,
    sample_ids: set[UUID],
    iou_threshold: float,
    confidence_threshold: float,
) -> common.EvaluationRunResult:
    """Run object-detection evaluation for one GT/prediction collection pair."""
    gt_annotations = load_annotations.load_object_detection_annotations(
        session,
        gt_collection_id,
        sample_ids=sample_ids,
    )
    pred_annotations = load_annotations.load_object_detection_annotations(
        session,
        prediction_collection_id,
        sample_ids=sample_ids,
    )

    all_label_ids = {annotation.label_id for annotation in gt_annotations} | {
        annotation.label_id for annotation in pred_annotations
    }
    label_names = load_annotations.load_label_names(session, all_label_ids)

    match_records = compute_od_metrics.match_annotations(
        gt_annotations,
        pred_annotations,
        iou_threshold,
        confidence_threshold,
    )
    pred_confidences = {
        annotation.annotation_id: annotation.confidence for annotation in pred_annotations
    }

    metrics: dict[str, object] = {
        "all": compute_od_metrics.compute_metrics(match_records, pred_confidences, label_names)
    }
    return common.EvaluationRunResult(metrics=metrics, match_records=match_records)
