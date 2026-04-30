"""Evaluation service dispatcher."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.evaluation_result import EvaluationResultTable, EvaluationTaskType
from lightly_studio.resolvers import evaluation_result_resolver
from lightly_studio.services.evaluation_service import (
    common,
    run_classification,
    run_instance_segmentation,
    run_object_detection,
)


def run_evaluation(  # noqa: PLR0913
    session: Session,
    dataset_id: UUID,
    name: str,
    gt_collection_name: str,
    prediction_collection_name: str,
    sample_ids: Sequence[UUID],
    task_type: EvaluationTaskType,
    iou_threshold: float = 0.5,
    confidence_threshold: float = 0.0,
) -> EvaluationResultTable:
    """Run one evaluation task and persist the result."""
    frozen_sample_ids = list(dict.fromkeys(sample_ids))
    sample_id_set = set(frozen_sample_ids)
    gt_collection, prediction_collection = common.resolve_annotation_collections(
        session=session,
        dataset_id=dataset_id,
        gt_collection_name=gt_collection_name,
        prediction_collection_name=prediction_collection_name,
    )

    if task_type == EvaluationTaskType.OBJECT_DETECTION:
        run_result = run_object_detection.run(
            session=session,
            gt_collection_id=gt_collection.collection_id,
            prediction_collection_id=prediction_collection.collection_id,
            sample_ids=sample_id_set,
            iou_threshold=iou_threshold,
            confidence_threshold=confidence_threshold,
        )
    elif task_type == EvaluationTaskType.CLASSIFICATION:
        run_result = run_classification.run(
            session=session,
            gt_collection_id=gt_collection.collection_id,
            prediction_collection_id=prediction_collection.collection_id,
            sample_ids=sample_id_set,
        )
    elif task_type == EvaluationTaskType.INSTANCE_SEGMENTATION:
        run_result = run_instance_segmentation.run(
            session=session,
            gt_collection_id=gt_collection.collection_id,
            prediction_collection_id=prediction_collection.collection_id,
            sample_ids=sample_id_set,
            iou_threshold=iou_threshold,
            confidence_threshold=confidence_threshold,
        )
    else:
        raise NotImplementedError(f"Evaluation task type '{task_type.value}' is not supported yet.")

    result = evaluation_result_resolver.create(
        session=session,
        dataset_id=dataset_id,
        name=name,
        gt_collection_id=gt_collection.id,
        prediction_collection_id=prediction_collection.id,
        task_type=task_type,
        iou_threshold=iou_threshold,
        confidence_threshold=confidence_threshold,
        metrics=run_result.metrics,
    )
    common.persist_sample_ids(session, result.id, frozen_sample_ids)
    common.persist_matches(session, result.id, run_result.match_records)
    session.commit()
    return result
