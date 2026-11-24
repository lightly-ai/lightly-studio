"""Read the labeling-workflow tables that the workflow service owns."""

from __future__ import annotations

from uuid import UUID

import sqlalchemy
from sqlmodel import Session, func, select

from lightly_studio.models.adjacents import AdjacentResultView
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
from lightly_studio.resolvers.mcap_group_sequence_resolver.mcap_sequence_filter import (
    McapSequenceFilter,
)
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter


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
    session: Session, dataset_id: UUID, project_id: UUID, assignee: str | None = None
) -> dict[WorkflowStatus, int]:
    """Count the dataset's samples per workflow status, project-wide or for one person.

    The counts ignore all grid filters. One query returns the batch file count per state
    and the dataset's sample count. "Not in workflow" is the sample count minus the
    batch file counts, because each batched sample is in at most one batch of the project.
    For an assignee, only the batch files they label or review count, and "Not in workflow"
    is 0, matching what `SampleFilter.set_workflow_assignee` lets them see.

    Args:
        session: The database session.
        dataset_id: The ID of the dataset, that is its root collection.
        project_id: The dataset's workflow project.
        assignee: Email of the person to count for, or None to count everyone's files.

    Returns:
        The sample count of every workflow status option, 0 for an empty state.
    """
    sample_total_label = "__sample_total__"
    batch_files = [batch_file_table.c.project_id == project_id]
    if assignee is not None:
        email = assignee.lower()
        batch_files.append(
            sqlalchemy.or_(
                func.lower(batch_file_table.c.labeler) == email,
                func.lower(batch_file_table.c.reviewer) == email,
            )
        )
    state_counts = (
        select(batch_file_table.c.state.label("key"), func.count().label("count"))
        .where(*batch_files)
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
    not_in_workflow = max(by_key.get(sample_total_label, 0) - batched, 0)
    counts[WorkflowStatus.NOT_IN_WORKFLOW] = 0 if assignee is not None else not_in_workflow
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
    workflow status options runs no workflow SQL. Only image and MCAP sequence filters
    filter by workflow status.

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


def scope_to_assignee(filters: ImageFilter | McapSequenceFilter, email: str) -> None:
    """Limit an image or MCAP sequence filter to one person's batch files.

    A filter without workflow status options gets all of them, so the person's view is
    limited whether or not they filter by status. A dataset without a workflow project is
    not limited.

    Args:
        filters: The filter to update in place.
        email: The person whose labeled or reviewed files stay visible.
    """
    if filters.sample_filter is None:
        filters.sample_filter = SampleFilter()
    if not filters.sample_filter.workflow_states:
        filters.sample_filter.workflow_states = list(WorkflowStatus)
    filters.sample_filter.set_workflow_assignee(email=email)


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


def get_samples_workflow(
    session: Session, project_id: UUID, sample_ids: list[UUID]
) -> dict[UUID, SampleWorkflowView]:
    """Get the batch and state of a few samples in a project, with one query.

    Args:
        session: The database session.
        project_id: The dataset's workflow project.
        sample_ids: The samples to look up.

    Returns:
        The batch and state of each sample that is in a batch of the project, by sample ID.
    """
    if not sample_ids:
        return {}
    rows = session.execute(
        select(
            batch_file_table.c.sample_id, batch_file_table.c.batch_id, batch_file_table.c.state
        ).where(
            batch_file_table.c.project_id == project_id,
            batch_file_table.c.sample_id.in_(sample_ids),
        )
    ).all()
    return {
        sample_id: SampleWorkflowView(
            project_id=project_id, batch_id=batch_id, state=WorkflowStatus(state)
        )
        for sample_id, batch_id, state in rows
    }


def add_neighbour_workflow(
    session: Session, result: AdjacentResultView, project_id: UUID
) -> AdjacentResultView:
    """Add the neighbours' batch and state, so the detail view can open them in workflow mode.

    Args:
        session: The database session.
        result: The adjacency result of a sample.
        project_id: The dataset's workflow project.

    Returns:
        A copy of the result with the previous and next neighbour's batch and state, None for
        a neighbour in no batch.
    """
    neighbour_ids = [
        neighbour_id
        for neighbour_id in (result.previous_sample_id, result.next_sample_id)
        if neighbour_id is not None
    ]
    workflows = get_samples_workflow(
        session=session, project_id=project_id, sample_ids=neighbour_ids
    )
    return result.model_copy(
        update={
            "previous_workflow": workflows.get(result.previous_sample_id)
            if result.previous_sample_id
            else None,
            "next_workflow": workflows.get(result.next_sample_id)
            if result.next_sample_id
            else None,
        }
    )


def _workflow_sample_filter(filters: GridFilterBase | None) -> SampleFilter | None:
    """Get the sample filter of a filter with workflow status options, else None."""
    sample_filter = (
        filters.sample_filter if isinstance(filters, (ImageFilter, McapSequenceFilter)) else None
    )
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
