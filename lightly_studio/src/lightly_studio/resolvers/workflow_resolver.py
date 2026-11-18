"""Read the labeling-workflow tables that the workflow service owns."""

from __future__ import annotations

from uuid import UUID

import sqlalchemy
from sqlmodel import Session, select

from lightly_studio.models.workflow import project_table
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
