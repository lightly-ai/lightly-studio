"""API routes for the labeling workflow of a dataset."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from lightly_studio.api.routes.api.collection import get_and_validate_collection_id
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.workflow import WorkflowStatus
from lightly_studio.resolvers import collection_resolver, workflow_resolver

workflow_router = APIRouter(tags=["workflow"])


class WorkflowProjectView(BaseModel):
    """The labeling-workflow project of a dataset."""

    project_id: UUID | None
    """The project ID, or None if the dataset has no project."""


@workflow_router.get("/collections/{collection_id}/workflow/project")
def get_workflow_project(
    session: SessionDep,
    collection: Annotated[CollectionTable, Depends(get_and_validate_collection_id)],
) -> WorkflowProjectView:
    """Get the labeling-workflow project of the collection's dataset.

    Args:
        session: Database session.
        collection: A collection of the dataset.

    Returns:
        The project of the dataset, if it has one.
    """
    dataset = collection_resolver.get_root_collection(
        session=session, collection_id=collection.collection_id
    )
    return WorkflowProjectView(
        project_id=workflow_resolver.get_project_id(
            session=session, dataset_id=dataset.collection_id
        )
    )


class WorkflowStatusCountsView(BaseModel):
    """The sample count of each workflow status option of a dataset."""

    counts: dict[WorkflowStatus, int] | None
    """The count per option, project-wide, or None if the dataset has no project."""


@workflow_router.get("/collections/{collection_id}/workflow/status-counts")
def get_workflow_status_counts(
    session: SessionDep,
    collection: Annotated[CollectionTable, Depends(get_and_validate_collection_id)],
) -> WorkflowStatusCountsView:
    """Count the samples of the collection's dataset per workflow status.

    The counts are project-wide and ignore the grid filters.

    Args:
        session: Database session.
        collection: A collection of the dataset.

    Returns:
        The count per workflow status option, or None counts if the dataset has no project.
    """
    dataset = collection_resolver.get_root_collection(
        session=session, collection_id=collection.collection_id
    )
    project_id = workflow_resolver.get_project_id(session=session, dataset_id=dataset.collection_id)
    if project_id is None:
        return WorkflowStatusCountsView(counts=None)
    return WorkflowStatusCountsView(
        counts=workflow_resolver.get_status_counts(
            session=session, dataset_id=dataset.collection_id, project_id=project_id
        )
    )
