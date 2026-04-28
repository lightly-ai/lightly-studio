"""Evaluation service — compute and persist COCO metrics."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.evaluation_result import EvaluationResultTable
from lightly_studio.models.tag import TagTable
from lightly_studio.resolvers import annotation_collection_resolver, evaluation_result_resolver
from lightly_studio.services.evaluation_service.compute_coco_metrics import compute_metrics_for_pair


def run_evaluation(
    session: Session,
    dataset_id: UUID,
    gt_collection_name: str,
    prediction_collection_names: list[str],
    tags: list[TagTable],
    iou_threshold: float = 0.5,
    confidence_threshold: float = 0.0,
) -> EvaluationResultTable:
    """Compute COCO metrics and persist the result.

    Metrics are computed for every (prediction_collection × subset) combination.
    Subsets always include "all" plus one entry per provided tag.

    Args:
        tags: Tag records to use as subsets. Typically loaded by the caller
              from the root image collection. Pass an empty list to compute
              only the "all" subset.
    """
    gt = annotation_collection_resolver.get_by_name(
        session=session, dataset_id=dataset_id, name=gt_collection_name
    )
    if gt is None:
        raise ValueError(f"Ground-truth collection '{gt_collection_name}' not found.")

    pred_collections = []
    for name in prediction_collection_names:
        coll = annotation_collection_resolver.get_by_name(
            session=session, dataset_id=dataset_id, name=name
        )
        if coll is None:
            raise ValueError(f"Prediction collection '{name}' not found.")
        pred_collections.append(coll)

    metrics: dict = {}
    for pred_coll in pred_collections:
        subsets: dict = {}

        # "all" subset — no tag filter
        subsets["all"] = compute_metrics_for_pair(
            session=session,
            gt_collection=gt,
            pred_collection=pred_coll,
            tag_id=None,
            iou_threshold=iou_threshold,
            confidence_threshold=confidence_threshold,
        )

        # One subset per tag
        for tag in tags:
            subsets[tag.name] = compute_metrics_for_pair(
                session=session,
                gt_collection=gt,
                pred_collection=pred_coll,
                tag_id=tag.tag_id,
                iou_threshold=iou_threshold,
                confidence_threshold=confidence_threshold,
            )

        metrics[pred_coll.name] = subsets

    return evaluation_result_resolver.create(
        session=session,
        dataset_id=dataset_id,
        gt_collection_id=gt.id,
        prediction_collection_ids=[c.id for c in pred_collections],
        iou_threshold=iou_threshold,
        confidence_threshold=confidence_threshold,
        metrics=metrics,
    )
