"""Add the results of a completed training process to the database."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.errors import NotFoundError
from lightly_studio.evaluation.image_dataset_evaluate import ObjectDetectionEvaluationConfig
from lightly_studio.models.evaluation_run import EvaluationTaskType
from lightly_studio.models.training_run import TrainingRunStatus
from lightly_studio.resolvers import collection_resolver
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.services import evaluation_service
from lightly_studio.services.training_service import ingest_predictions
from lightly_studio.services.training_service.training_run_registry import TrainingRun


def finish_training_run(session: Session, run: TrainingRun) -> None:
    """Add the predictions as an annotation source and evaluate them on the val samples.

    The prediction annotation source and the evaluation run get the name of the run.
    """
    collection = collection_resolver.get_by_id(session=session, collection_id=run.collection_id)
    if collection is None:
        raise NotFoundError(f"Collection {run.collection_id} not found.")

    run.status = TrainingRunStatus.INGESTING
    ingest_predictions.ingest_predictions(
        session=session,
        collection_id=collection.collection_id,
        dataset_id=collection.dataset_id,
        predictions_file=run.files.predictions_file,
        annotation_source=run.name,
    )

    run.status = TrainingRunStatus.EVALUATING
    # Evaluate on the val samples at the start of the run, not on the current val tag.
    result = evaluation_service.run_evaluation(
        session=session,
        collection=collection,
        task_type=EvaluationTaskType.OBJECT_DETECTION,
        gt_annotation_source=run.gt_annotation_source,
        pred_annotation_source=run.name,
        config=ObjectDetectionEvaluationConfig(compute_average_precision=True),
        filters=ImageFilter(sample_filter=SampleFilter(sample_ids=run.val_sample_ids)),
        name=run.name,
    )
    run.evaluation_run_id = result.evaluation_run_id
