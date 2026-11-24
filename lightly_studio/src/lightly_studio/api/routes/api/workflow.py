"""API routes for the labeling workflow of a dataset."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from lightly_studio.api.dependencies.identity import IdentityDep
from lightly_studio.api.dependencies.workflow_scope import workflow_assignee
from lightly_studio.api.routes.api.collection import get_and_validate_collection_id
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.workflow import WorkflowStatus
from lightly_studio.resolvers import annotation_resolver, collection_resolver, workflow_resolver

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
    """The count per option, or None if the dataset has no project.

    Project-wide, except for a labeler account: then only their own batch files count.
    """


@workflow_router.get("/collections/{collection_id}/workflow/status-counts")
def get_workflow_status_counts(
    session: SessionDep,
    identity: IdentityDep,
    collection: Annotated[CollectionTable, Depends(get_and_validate_collection_id)],
) -> WorkflowStatusCountsView:
    """Count the samples of the collection's dataset per workflow status.

    The counts ignore the grid filters. They are project-wide, but a labeler account counts
    only the batch files it labels or reviews, the files its grid shows.

    Args:
        session: Database session.
        identity: The user; a labeler gets the counts of their own files.
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
            session=session,
            dataset_id=dataset.collection_id,
            project_id=project_id,
            assignee=workflow_assignee(identity=identity),
        )
    )


class WorkflowObjectCountsRequest(BaseModel):
    """The samples to count the objects of."""

    sample_ids: list[UUID]
    """Samples of the dataset, for example the files of a batch."""


class WorkflowObjectCountsView(BaseModel):
    """The object count of each requested sample."""

    counts: dict[UUID, int]
    """The count per sample. A sequence counts the annotations on all of its ticks."""


@workflow_router.post("/collections/{collection_id}/workflow/object-counts")
def count_workflow_objects(
    session: SessionDep,
    collection: Annotated[CollectionTable, Depends(get_and_validate_collection_id)],
    body: WorkflowObjectCountsRequest,
) -> WorkflowObjectCountsView:
    """Count the objects of each sample, for the workflow service's batch object counts.

    Args:
        session: Database session.
        collection: The collection the samples belong to, usually the dataset.
        body: The samples to count.

    Returns:
        The object count of each requested sample, 0 for samples outside the collection.
    """
    return WorkflowObjectCountsView(
        counts=annotation_resolver.count_objects_by_sample_ids(
            session=session,
            collection_id=collection.collection_id,
            sample_ids=body.sample_ids,
        )
    )
