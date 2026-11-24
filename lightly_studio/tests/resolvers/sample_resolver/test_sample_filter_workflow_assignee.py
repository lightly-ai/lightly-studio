"""Tests for limiting the workflow status filter to one person's batch files."""

from __future__ import annotations

from collections.abc import Generator
from uuid import UUID

import pytest
from sqlmodel import Session, select

from lightly_studio.models.sample import SampleTable
from lightly_studio.models.workflow import WorkflowStatus
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests import helpers_workflow
from tests.helpers_resolvers import ImageStub, create_collection, create_images

# Who labels and reviews each image; "loose.png" is in no batch.
FILES = {
    "mine.png": ("me@example.com", "rev@example.com"),
    "reviewed.png": ("other@example.com", "me@example.com"),
    "theirs.png": ("other@example.com", "rev@example.com"),
}


@pytest.fixture
def project(db_session: Session) -> Generator[tuple[UUID, dict[str, UUID]], None, None]:
    """A dataset whose images are in batches of different people, plus one loose image.

    Yields:
        The project id, and the image sample id for each file name.
    """
    with helpers_workflow.workflow_tables(session=db_session):
        collection = create_collection(session=db_session)
        images = create_images(
            db_session=db_session,
            collection_id=collection.collection_id,
            images=[ImageStub(path=path) for path in [*FILES, "loose.png"]],
        )
        by_name = {
            name: next(image.sample_id for image in images if image.file_path_abs.endswith(name))
            for name in [*FILES, "loose.png"]
        }
        project_id = helpers_workflow.create_project(
            session=db_session, dataset_id=collection.collection_id
        )
        for name, (labeler, reviewer) in FILES.items():
            helpers_workflow.add_batch_files(
                session=db_session,
                project_id=project_id,
                states={by_name[name]: "in_progress"},
                labeler=labeler,
                reviewer=reviewer,
            )
        yield project_id, by_name


@pytest.mark.parametrize("email", ["me@example.com", "Me@Example.com"])
def test_apply__assignee_sees_only_their_files(
    db_session: Session, project: tuple[UUID, dict[str, UUID]], email: str
) -> None:
    project_id, by_name = project
    sample_filter = SampleFilter(workflow_states=list(WorkflowStatus))
    sample_filter.set_workflow_project_id(project_id=project_id)
    sample_filter.set_workflow_assignee(email=email)

    assert _sample_ids(session=db_session, sample_filter=sample_filter) == {
        by_name["mine.png"],
        by_name["reviewed.png"],
    }


def test_apply__assignee_sees_no_loose_samples(
    db_session: Session, project: tuple[UUID, dict[str, UUID]]
) -> None:
    project_id, _ = project
    sample_filter = SampleFilter(workflow_states=[WorkflowStatus.NOT_IN_WORKFLOW])
    sample_filter.set_workflow_project_id(project_id=project_id)
    sample_filter.set_workflow_assignee(email="me@example.com")

    assert _sample_ids(session=db_session, sample_filter=sample_filter) == set()


def test_apply__no_assignee_sees_everyone(
    db_session: Session, project: tuple[UUID, dict[str, UUID]]
) -> None:
    project_id, by_name = project
    sample_filter = SampleFilter(workflow_states=list(WorkflowStatus))
    sample_filter.set_workflow_project_id(project_id=project_id)

    assert _sample_ids(session=db_session, sample_filter=sample_filter) == set(by_name.values())


def test_apply__assignee_without_project_sees_everything(db_session: Session) -> None:
    sample_filter = SampleFilter(workflow_states=list(WorkflowStatus))
    sample_filter.set_workflow_project_id(project_id=None)
    sample_filter.set_workflow_assignee(email="me@example.com")

    with helpers_workflow.workflow_tables(session=db_session):
        images = create_images(
            db_session=db_session,
            collection_id=create_collection(session=db_session).collection_id,
            images=[ImageStub(path="a.png")],
        )
        assert _sample_ids(session=db_session, sample_filter=sample_filter) == {images[0].sample_id}


def _sample_ids(session: Session, sample_filter: SampleFilter) -> set[UUID]:
    query = sample_filter.apply(select(SampleTable.sample_id))
    return set(session.exec(query).all())
