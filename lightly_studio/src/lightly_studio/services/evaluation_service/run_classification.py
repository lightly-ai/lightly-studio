"""Classification evaluation runner."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.services.evaluation_service import (
    common,
    compute_classification_metrics,
    load_annotations,
)


def run(
    session: Session,
    gt_collection_id: UUID,
    prediction_collection_id: UUID,
    sample_ids: set[UUID],
) -> common.EvaluationRunResult:
    """Run single-label classification evaluation for one GT/prediction pair."""
    gt_annotations = load_annotations.load_classification_annotations(
        session,
        gt_collection_id,
        sample_ids=sample_ids,
    )
    pred_annotations = load_annotations.load_classification_annotations(
        session,
        prediction_collection_id,
        sample_ids=sample_ids,
    )

    all_label_ids = {annotation.label_id for annotation in gt_annotations} | {
        annotation.label_id for annotation in pred_annotations
    }
    label_names = load_annotations.load_label_names(session, all_label_ids)

    match_records, total_gt_samples = compute_classification_metrics.match_annotations(
        gt_annotations, pred_annotations
    )

    metrics: dict[str, object] = {
        "all": compute_classification_metrics.compute_metrics(
            match_records,
            total_gt_samples=total_gt_samples,
            label_names=label_names,
        )
    }
    return common.EvaluationRunResult(metrics=metrics, match_records=match_records)
