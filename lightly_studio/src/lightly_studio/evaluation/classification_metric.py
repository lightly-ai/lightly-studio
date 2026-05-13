"""Classification evaluation metric primitives."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.evaluation.evaluation_data import EvaluationData
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.evaluation_sample_metric import EvaluationSampleMetricCreate
from lightly_studio.resolvers import evaluation_sample_metric_resolver

METRIC_BATCH_SIZE = 32  # Buffer size for evaluation_sample_metric_resolver.create_many


def create_and_persist_classification_metrics_per_sample(
    session: Session,
    data: EvaluationData,
) -> None:
    """Create and persist per-sample classification metrics.

    For each selected sample, writes two metric rows: ``is_correct`` (1.0 if the
    prediction's label matches the ground truth, 0.0 otherwise) and
    ``confidence`` (the prediction's confidence).

    Each selected sample must have exactly one ground-truth annotation and
    exactly one prediction annotation in their respective annotation collections,
    and the prediction must have a non-None confidence. Validation runs in a
    first pass over all samples before any persistence, so nothing is written
    on error.

    Raises:
        ValueError: If any selected sample has 0 or >1 GT/prediction annotations,
            or if a prediction has a None confidence.
    """
    # Pass 1: validate all samples up front, before any persistence.
    gt_by_sample: dict[UUID, AnnotationBaseTable] = {}
    pred_by_sample: dict[UUID, AnnotationBaseTable] = {}
    for sample_id in data.selected_sample_ids:
        gt = _require_single(
            annotations=data.gt_per_sample.get(sample_id, []),
            sample_id=sample_id,
            kind="ground truth",
        )
        pred = _require_single(
            annotations=data.pred_per_sample.get(sample_id, []),
            sample_id=sample_id,
            kind="prediction",
        )
        if pred.confidence is None:
            raise ValueError(
                f"Classification evaluation expected a non-None prediction confidence "
                f"for sample {sample_id}, got None."
            )
        gt_by_sample[sample_id] = gt
        pred_by_sample[sample_id] = pred

    # Pass 2: build and persist metrics in batches.
    metrics_to_persist: list[EvaluationSampleMetricCreate] = []
    for sample_id in data.selected_sample_ids:
        gt = gt_by_sample[sample_id]
        pred = pred_by_sample[sample_id]
        # pred.confidence is guaranteed non-None by pass 1, but mypy can't see that.
        assert pred.confidence is not None
        is_correct = 1.0 if pred.annotation_label_id == gt.annotation_label_id else 0.0
        metrics_to_persist.extend(
            [
                EvaluationSampleMetricCreate(
                    evaluation_run_id=data.evaluation_run_id,
                    sample_id=sample_id,
                    metric_name="is_correct",
                    value=is_correct,
                ),
                EvaluationSampleMetricCreate(
                    evaluation_run_id=data.evaluation_run_id,
                    sample_id=sample_id,
                    metric_name="confidence",
                    value=float(pred.confidence),
                ),
            ]
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


def _require_single(
    annotations: list[AnnotationBaseTable], *, sample_id: UUID, kind: str
) -> AnnotationBaseTable:
    """Return the lone annotation, or raise if there are 0 or >1."""
    if len(annotations) != 1:
        raise ValueError(
            f"Classification evaluation expected exactly 1 {kind} annotation for "
            f"sample {sample_id}, found {len(annotations)}."
        )
    return annotations[0]
