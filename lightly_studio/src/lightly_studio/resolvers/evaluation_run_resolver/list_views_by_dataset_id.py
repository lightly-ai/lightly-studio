"""Build API views of a dataset's evaluation runs."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.evaluation_run import EvaluationRunTable, EvaluationRunView
from lightly_studio.resolvers import collection_resolver, tag_resolver
from lightly_studio.resolvers.evaluation_run_resolver.get_all_by_dataset_id import (
    get_all_by_dataset_id,
)


def list_views_by_dataset_id(
    session: Session,
    dataset_id: UUID,
) -> list[EvaluationRunView]:
    """Return API views of all evaluation runs for a dataset, newest first.

    Resolves each run's ground-truth and prediction collection IDs to their
    source names so the view is self-describing.

    Args:
        session: Database session used by resolver calls.
        dataset_id: The dataset whose evaluation runs are listed.

    Returns:
        Views of the runs, newest first.
    """
    runs = get_all_by_dataset_id(session=session, dataset_id=dataset_id)
    collection_name_by_id = collection_resolver.get_names_by_ids(
        session=session,
        collection_ids={run.gt_annotation_collection_id for run in runs}
        | {run.pred_annotation_collection_id for run in runs},
    )
    tag_name_by_id = tag_resolver.get_names_by_ids(
        session=session,
        tag_ids=[tag_id for run in runs for tag_id in _scope_tag_ids(run=run)],
    )
    return [
        EvaluationRunView(
            id=run.id,
            name=run.name,
            task_type=run.task_type,
            evaluation_run_configuration=run.config_json,
            created_at=run.created_at,
            gt_annotation_source=collection_name_by_id.get(run.gt_annotation_collection_id),
            pred_annotation_source=collection_name_by_id.get(run.pred_annotation_collection_id),
            stale_since=run.stale_since,
            scope_tag_names=[
                tag_name_by_id[tag_id]
                for tag_id in _scope_tag_ids(run=run)
                if tag_id in tag_name_by_id
            ],
        )
        for run in runs
    ]


def _scope_tag_ids(run: EvaluationRunTable) -> list[UUID]:
    """Return the tag IDs of the stored image filter of a run, or none."""
    if run.sample_scope_json is None:
        return []
    sample_filter = run.sample_scope_json["filter"].get("sample_filter") or {}
    return [UUID(tag_id) for tag_id in sample_filter.get("tag_ids") or []]
