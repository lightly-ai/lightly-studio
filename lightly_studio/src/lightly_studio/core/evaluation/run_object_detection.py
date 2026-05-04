"""Object-detection evaluation runner."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.core.evaluation import common, compute_od_metrics, load_annotations


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

    label_names = load_annotations.load_label_names_for_annotations(
        session, gt_annotations, pred_annotations
    )

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
    annotation_results, sample_metrics = common.build_results_from_matches(
        match_records, include_iou=True
    )
    return common.EvaluationRunResult(
        metrics=metrics,
        annotation_results=annotation_results,
        sample_metrics=sample_metrics,
    )
