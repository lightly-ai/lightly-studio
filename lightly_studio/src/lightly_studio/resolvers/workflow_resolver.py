"""Read the labeling-workflow tables that the workflow service owns."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import sqlalchemy
from sqlalchemy import ColumnElement, Row, Select
from sqlalchemy.orm import Mapped
from sqlmodel import Session, func, select

from lightly_studio.models.sample import SampleTable
from lightly_studio.models.workflow import (
    SampleWorkflowView,
    WorkflowStatus,
    batch_file_table,
    project_table,
)
from lightly_studio.resolvers import collection_resolver
from lightly_studio.resolvers.grid_filter_base import GridFilterBase
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter

_BATCH_ID_LABEL = "workflow_batch_id"
_STATE_LABEL = "workflow_state"


def get_project_id(session: Session, dataset_id: UUID) -> UUID | None:
    """Get the workflow project of a dataset.

    Args:
        session: The database session.
        dataset_id: The ID of the dataset, that is its root collection.

    Returns:
        The project ID, or None if the dataset has no project or the database has no
        workflow tables (Studio without the workflow service).
    """
    if not _has_workflow_tables(session=session):
        return None
    return _select_project_id(session=session, dataset_id=dataset_id)


def get_status_counts(
    session: Session, dataset_id: UUID, project_id: UUID
) -> dict[WorkflowStatus, int]:
    """Count the dataset's samples per workflow status, project-wide.

    The counts ignore all grid filters. One query returns the batch file count per state
    and the dataset's sample count. "Not in workflow" is the sample count minus the
    batch file counts, because each batched sample is in at most one batch of the project.

    Args:
        session: The database session.
        dataset_id: The ID of the dataset, that is its root collection.
        project_id: The dataset's workflow project.

    Returns:
        The sample count of every workflow status option, 0 for an empty state.
    """
    sample_total_label = "__sample_total__"
    state_counts = (
        select(batch_file_table.c.state.label("key"), func.count().label("count"))
        .where(batch_file_table.c.project_id == project_id)
        .group_by(batch_file_table.c.state)
    )
    sample_total = (
        select(
            sqlalchemy.literal(sample_total_label).label("key"),
            func.count().label("count"),
        )
        .select_from(SampleTable)
        .where(SampleTable.collection_id == dataset_id)
    )
    rows = session.execute(sqlalchemy.union_all(state_counts, sample_total)).all()
    by_key = {key: int(count) for key, count in rows}

    counts = {status: by_key.get(status.value, 0) for status in WorkflowStatus}
    batched = sum(
        count for status, count in counts.items() if status != WorkflowStatus.NOT_IN_WORKFLOW
    )
    counts[WorkflowStatus.NOT_IN_WORKFLOW] = max(by_key.get(sample_total_label, 0) - batched, 0)
    return counts


def get_dataset_project_id(session: Session, collection_id: UUID) -> UUID | None:
    """Get the workflow project of the dataset that a collection belongs to.

    Args:
        session: The database session.
        collection_id: The ID of a collection of the dataset.

    Returns:
        The project ID, or None if the collection does not exist, the dataset has no project
        or the database has no workflow tables.
    """
    if not _has_workflow_tables(session=session):
        return None
    try:
        dataset = collection_resolver.get_root_collection(
            session=session, collection_id=collection_id
        )
    except ValueError:
        return None
    return _select_project_id(session=session, dataset_id=dataset.collection_id)


def resolve_sample_filter(
    session: Session, collection_id: UUID, filters: GridFilterBase | None
) -> None:
    """Set the workflow project on a filter that filters by workflow status.

    Looks up the project once, from the dataset of the collection. A filter without
    workflow status options runs no workflow SQL. Only image filters filter by workflow status.

    Args:
        session: The database session.
        collection_id: The ID of the collection that the filter applies to.
        filters: The filter to update in place.
    """
    if not filters_by_workflow_status(filters=filters):
        return
    set_filter_project_id(
        filters=filters,
        project_id=get_dataset_project_id(session=session, collection_id=collection_id),
    )


def filters_by_workflow_status(filters: GridFilterBase | None) -> bool:
    """Whether a filter has workflow status options."""
    return _workflow_sample_filter(filters=filters) is not None


def set_filter_project_id(filters: GridFilterBase | None, project_id: UUID | None) -> None:
    """Set an already looked-up workflow project on a filter with workflow status options.

    Does nothing for a filter without workflow status options.

    Args:
        filters: The filter to update in place.
        project_id: The project of the dataset that the filter applies to.
    """
    sample_filter = _workflow_sample_filter(filters=filters)
    if sample_filter is not None:
        sample_filter.set_workflow_project_id(project_id=project_id)


def add_sample_workflow_columns(
    query: Select[Any], sample_id_column: ColumnElement[UUID] | Mapped[UUID], project_id: UUID
) -> Select[Any]:
    """Add each sample's batch and state in the project to a query, with one LEFT JOIN.

    Read the values back from each row with `get_sample_workflow`.

    Args:
        query: The query that selects samples.
        sample_id_column: The sample ID column of the query.
        project_id: The dataset's workflow project.

    Returns:
        The query, with the batch ID and the state added to the SELECT list.
    """
    # An alias, so the workflow status filter's subqueries on `batch_file` don't correlate to
    # this join.
    sample_batch_file = batch_file_table.alias("sample_batch_file")
    return query.outerjoin(
        sample_batch_file,
        sqlalchemy.and_(
            sample_batch_file.c.sample_id == sample_id_column,
            sample_batch_file.c.project_id == project_id,
        ),
    ).add_columns(
        sample_batch_file.c.batch_id.label(_BATCH_ID_LABEL),
        sample_batch_file.c.state.label(_STATE_LABEL),
    )


def get_sample_workflow(row: Row[Any], project_id: UUID) -> SampleWorkflowView | None:
    """Read a sample's batch and state from a row of `add_sample_workflow_columns`.

    Args:
        row: A row of a query that `add_sample_workflow_columns` changed.
        project_id: The project passed to `add_sample_workflow_columns`.

    Returns:
        The sample's batch and state, or None if the sample is in no batch of the project.
    """
    batch_id = getattr(row, _BATCH_ID_LABEL, None)
    if batch_id is None:
        return None
    return SampleWorkflowView(
        project_id=project_id,
        batch_id=batch_id,
        state=WorkflowStatus(getattr(row, _STATE_LABEL)),
    )


def _workflow_sample_filter(filters: GridFilterBase | None) -> SampleFilter | None:
    """Get the sample filter of a filter with workflow status options, else None."""
    sample_filter = filters.sample_filter if isinstance(filters, ImageFilter) else None
    if sample_filter is None or not sample_filter.workflow_states:
        return None
    return sample_filter


def _select_project_id(session: Session, dataset_id: UUID) -> UUID | None:
    return session.exec(
        select(project_table.c.id).where(project_table.c.dataset_id == dataset_id)
    ).one_or_none()


def _has_workflow_tables(session: Session) -> bool:
    query = sqlalchemy.text(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema = 'workflow' AND table_name = 'project'"
    )
    return session.execute(query).first() is not None
