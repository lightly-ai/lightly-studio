"""Classification evaluation metric primitives."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.evaluation.evaluation_data import EvaluationData
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.evaluation_annotation_metric import EvaluationAnnotationMetricCreate
from lightly_studio.models.evaluation_sample_metric import EvaluationSampleMetricCreate
from lightly_studio.resolvers import (
    evaluation_annotation_metric_resolver,
    evaluation_sample_metric_resolver,
)

METRIC_BATCH_SIZE = 32  # Buffer size for evaluation_sample_metric_resolver.create_many


def create_and_persist_classification_metrics_per_sample(
    session: Session,
    data: EvaluationData,
) -> None:
    """Create and persist per-sample classification metrics.

    For each selected sample, writes a single ``disagreement`` metric row in
    ``[0, 1]``. Higher values indicate stronger disagreement between the ground
    truth and the prediction. The score is ``1 - c`` when labels match and
    ``c`` when they differ, where ``c`` is the prediction's confidence. If the
    prediction's confidence is ``None`` (e.g. annotator-vs-annotator
    comparisons), ``c`` defaults to ``1.0``, which degrades the score to a
    binary 0/1.

    Each selected sample must have exactly one ground-truth annotation and
    exactly one prediction annotation in their respective annotation source.
    All validation runs and metric rows are built before any persistence, so
    nothing is written on error.

    Raises:
        ValueError: If any selected sample has 0 or >1 GT/prediction annotations.
    """
    # Pass 1: validate every sample and build all metric rows up front, before
    # any persistence. Reading ORM attributes here is safe because no commit has
    # happened yet — pass 2's batch commits would otherwise expire the ORM rows
    # (expire_on_commit=True) and force lazy reloads on later reads.
    metrics_to_persist: list[EvaluationSampleMetricCreate] = []
    annotation_metrics_to_persist: list[EvaluationAnnotationMetricCreate] = []
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
        confidence = 1.0 if pred.confidence is None else float(pred.confidence)
        labels_agree = pred.annotation_label_id == gt.annotation_label_id
        disagreement = (1.0 - confidence) if labels_agree else confidence
        metrics_to_persist.append(
            EvaluationSampleMetricCreate(
                evaluation_run_id=data.evaluation_run_id,
                sample_id=sample_id,
                metric_name="disagreement",
                value=disagreement,
            )
        )
        annotation_metrics_to_persist.append(
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=data.evaluation_run_id,
                sample_id=sample_id,
                pred_annotation_id=pred.sample_id,
                gt_annotation_id=gt.sample_id,
                metric_name="disagreement",
                value=disagreement,
            )
        )

    # Pass 2: persist in batches. No ORM reads here, so commits are safe.
    for batch_start in range(0, len(metrics_to_persist), METRIC_BATCH_SIZE):
        evaluation_sample_metric_resolver.create_many(
            session=session,
            records=metrics_to_persist[batch_start : batch_start + METRIC_BATCH_SIZE],
        )
        evaluation_annotation_metric_resolver.create_many(
            session=session,
            records=annotation_metrics_to_persist[batch_start : batch_start + METRIC_BATCH_SIZE],
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
