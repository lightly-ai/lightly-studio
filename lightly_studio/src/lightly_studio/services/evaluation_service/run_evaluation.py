"""Orchestrate a single evaluation run.

Resolves the samples to evaluate (optionally filtered), builds the
``ImageDatasetEvaluate`` facade, and dispatches to the task-specific method.
Kept out of the route handler so it can be unit-tested without the HTTP layer
and reused by other callers.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Union

from sqlmodel import Session

from lightly_studio.evaluation.image_dataset_evaluate import (
    ClassificationEvaluationConfig,
    EvaluationResult,
    ImageDatasetEvaluate,
    ObjectDetectionEvaluationConfig,
    SemanticSegmentationEvaluationConfig,
)
from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.models.evaluation_run import EvaluationTaskType
from lightly_studio.resolvers import collection_resolver, image_resolver
from lightly_studio.resolvers.image_filter import ImageFilter

EvaluationConfig = Union[
    ObjectDetectionEvaluationConfig,
    ClassificationEvaluationConfig,
    SemanticSegmentationEvaluationConfig,
]


def run_evaluation(  # noqa: PLR0913
    session: Session,
    *,
    collection: CollectionTable,
    task_type: EvaluationTaskType,
    gt_annotation_source: str,
    pred_annotation_source: str,
    config: EvaluationConfig,
    filters: ImageFilter | None = None,
    name: str | None = None,
) -> EvaluationResult:
    """Run an evaluation for ``collection`` and persist it.

    The task is selected by the concrete type of ``config`` (which also carries
    the task-specific options). ``filters`` scopes the evaluated samples; when
    omitted the whole collection is evaluated. ``name`` defaults to
    ``"<task_type> <UTC timestamp>"`` (with microsecond precision so concurrent
    triggers don't collide on the ``(name, dataset_id)`` uniqueness constraint)
    when not provided.

    Args:
        session: Database session.
        collection: The image collection (active view) to evaluate.
        task_type: Evaluation task type, used for the default run name.
        gt_annotation_source: Name of the ground-truth annotation source.
        pred_annotation_source: Name of the prediction annotation source.
        config: Task-specific config; its type selects the evaluation task.
        filters: Optional active-view filter; evaluates all samples if omitted.
        name: Optional run name; auto-generated when omitted.

    Returns:
        Summary of the created run, including its ID and input counts.

    Raises:
        ValueError: If ``collection`` is not an image collection, the same
            annotation source is used for GT and predictions, or a source is
            missing or has the wrong annotation type. Mapped to 400 by the
            global exception handler.
    """
    if collection.sample_type != SampleType.IMAGE:
        raise ValueError("Evaluation can only be triggered on image collections.")

    root_collection = collection_resolver.get_root_collection(
        session=session, collection_id=collection.collection_id
    )
    sample_ids = image_resolver.get_sample_ids(
        session=session,
        collection_id=collection.collection_id,
        filters=filters,
    )
    evaluator = ImageDatasetEvaluate(
        session=session,
        collection_id=root_collection.collection_id,
        sample_ids=sample_ids,
    )
    run_name = (
        name or f"{task_type.value} {datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S.%f}"
    )

    if isinstance(config, ObjectDetectionEvaluationConfig):
        return evaluator.object_detection(
            name=run_name,
            gt_annotation_source=gt_annotation_source,
            pred_annotation_source=pred_annotation_source,
            config=config,
        )
    if isinstance(config, ClassificationEvaluationConfig):
        return evaluator.classification(
            name=run_name,
            gt_annotation_source=gt_annotation_source,
            pred_annotation_source=pred_annotation_source,
            config=config,
        )
    return evaluator.semantic_segmentation(
        name=run_name,
        gt_annotation_source=gt_annotation_source,
        pred_annotation_source=pred_annotation_source,
        config=config,
    )
