"""Read the labeling-workflow tables that the workflow service owns."""

from __future__ import annotations

from uuid import UUID

import sqlalchemy
from sqlmodel import Session, func, select

from lightly_studio.models.sample import SampleTable
from lightly_studio.models.workflow import WorkflowStatus, batch_file_table, project_table
from lightly_studio.resolvers import collection_resolver
from lightly_studio.resolvers.grid_filter_base import GridFilterBase
from lightly_studio.resolvers.image_filter import ImageFilter


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
    return session.exec(
        select(project_table.c.id).where(project_table.c.dataset_id == dataset_id)
    ).one_or_none()


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
    sample_filter = filters.sample_filter if isinstance(filters, ImageFilter) else None
    if sample_filter is None or not sample_filter.workflow_states:
        return
    dataset = collection_resolver.get_root_collection(session=session, collection_id=collection_id)
    sample_filter.set_workflow_project_id(
        project_id=get_project_id(session=session, dataset_id=dataset.collection_id)
    )


def _has_workflow_tables(session: Session) -> bool:
    query = sqlalchemy.text(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema = 'workflow' AND table_name = 'project'"
    )
    return session.execute(query).first() is not None
