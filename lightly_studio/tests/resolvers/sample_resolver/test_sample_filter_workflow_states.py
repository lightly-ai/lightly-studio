"""Tests for the workflow status part of SampleFilter."""

from __future__ import annotations

from collections.abc import Generator
from uuid import UUID, uuid4

import pytest
from sqlmodel import Session, select

from lightly_studio.models.sample import SampleTable
from lightly_studio.models.workflow import WorkflowStatus
from lightly_studio.resolvers import tag_resolver
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests import helpers_workflow
from tests.helpers_resolvers import ImageStub, create_collection, create_images, create_tag

# One image per workflow state, plus one image that is in no batch.
PATHS = {
    "not_started": "a.png",
    "in_progress": "b.png",
    "in_review": "c.png",
    "rework": "d.png",
    "accepted": "e.png",
    "not_in_workflow": "f.png",
}


@pytest.fixture
def project(db_session: Session) -> Generator[tuple[UUID, dict[str, UUID]], None, None]:
    """A dataset with one image per option, and its workflow project.

    Yields:
        The project id, and the image sample id for each option.
    """
    with helpers_workflow.workflow_tables(session=db_session):
        collection = create_collection(session=db_session)
        images = create_images(
            db_session=db_session,
            collection_id=collection.collection_id,
            images=[ImageStub(path=path) for path in PATHS.values()],
        )
        by_option = {
            option: next(image.sample_id for image in images if image.file_path_abs.endswith(path))
            for option, path in PATHS.items()
        }
        project_id = helpers_workflow.create_project(
            session=db_session, dataset_id=collection.collection_id
        )
        helpers_workflow.add_batch_files(
            session=db_session,
            project_id=project_id,
            states={
                sample_id: option
                for option, sample_id in by_option.items()
                if option != "not_in_workflow"
            },
        )
        yield project_id, by_option


@pytest.mark.parametrize("option", list(PATHS))
def test_apply__each_option(
    db_session: Session, project: tuple[UUID, dict[str, UUID]], option: str
) -> None:
    project_id, by_option = project
    sample_filter = SampleFilter(workflow_states=[WorkflowStatus(option)])
    sample_filter.set_workflow_project_id(project_id=project_id)

    assert _sample_ids(session=db_session, sample_filter=sample_filter) == {by_option[option]}


def test_apply__options_combine_with_or(
    db_session: Session, project: tuple[UUID, dict[str, UUID]]
) -> None:
    project_id, by_option = project
    sample_filter = SampleFilter(
        workflow_states=[
            WorkflowStatus.IN_REVIEW,
            WorkflowStatus.ACCEPTED,
            WorkflowStatus.NOT_IN_WORKFLOW,
        ]
    )
    sample_filter.set_workflow_project_id(project_id=project_id)

    assert _sample_ids(session=db_session, sample_filter=sample_filter) == {
        by_option["in_review"],
        by_option["accepted"],
        by_option["not_in_workflow"],
    }


def test_apply__all_options_match_all(
    db_session: Session, project: tuple[UUID, dict[str, UUID]]
) -> None:
    project_id, by_option = project
    sample_filter = SampleFilter(workflow_states=list(WorkflowStatus))
    sample_filter.set_workflow_project_id(project_id=project_id)

    assert _sample_ids(session=db_session, sample_filter=sample_filter) == set(by_option.values())


def test_apply__combines_with_tags_with_and(
    db_session: Session, project: tuple[UUID, dict[str, UUID]]
) -> None:
    project_id, by_option = project
    collection_id = db_session.exec(select(SampleTable.collection_id)).first()
    assert collection_id is not None
    tag = create_tag(session=db_session, collection_id=collection_id)
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session,
        tag_id=tag.tag_id,
        sample_ids=[by_option["in_review"], by_option["rework"]],
    )
    sample_filter = SampleFilter(
        tag_ids=[tag.tag_id],
        workflow_states=[WorkflowStatus.IN_REVIEW, WorkflowStatus.ACCEPTED],
    )
    sample_filter.set_workflow_project_id(project_id=project_id)

    assert _sample_ids(session=db_session, sample_filter=sample_filter) == {by_option["in_review"]}


def test_apply__ignores_other_projects(
    db_session: Session, project: tuple[UUID, dict[str, UUID]]
) -> None:
    _, by_option = project
    sample_filter = SampleFilter(workflow_states=[WorkflowStatus.IN_REVIEW])
    sample_filter.set_workflow_project_id(project_id=uuid4())

    assert _sample_ids(session=db_session, sample_filter=sample_filter) == set()

    sample_filter = SampleFilter(workflow_states=[WorkflowStatus.NOT_IN_WORKFLOW])
    sample_filter.set_workflow_project_id(project_id=uuid4())

    assert _sample_ids(session=db_session, sample_filter=sample_filter) == set(by_option.values())


def test_apply__no_project(db_session: Session) -> None:
    """Without a project, every sample is "Not in workflow" and no workflow table is read."""
    collection = create_collection(session=db_session)
    images = create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path="a.png"), ImageStub(path="b.png")],
    )

    in_review = SampleFilter(workflow_states=[WorkflowStatus.IN_REVIEW])
    in_review.set_workflow_project_id(project_id=None)
    not_in_workflow = SampleFilter(workflow_states=[WorkflowStatus.NOT_IN_WORKFLOW])
    not_in_workflow.set_workflow_project_id(project_id=None)

    # The workflow tables do not exist here, so any workflow SQL would fail.
    assert _sample_ids(session=db_session, sample_filter=in_review) == set()
    assert _sample_ids(session=db_session, sample_filter=not_in_workflow) == {
        image.sample_id for image in images
    }


def test_apply__empty_options(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    images = create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path="a.png")],
    )

    sample_filter = SampleFilter(workflow_states=[])

    assert _sample_ids(session=db_session, sample_filter=sample_filter) == {images[0].sample_id}


def test_apply__project_not_resolved() -> None:
    sample_filter = SampleFilter(workflow_states=[WorkflowStatus.IN_REVIEW])

    with pytest.raises(ValueError, match="workflow project"):
        sample_filter.apply(select(SampleTable))


def test_workflow_project_id__not_in_request_body() -> None:
    sample_filter = SampleFilter.model_validate(
        {"workflow_states": ["in_review"], "workflow_project_id": str(uuid4())}
    )

    with pytest.raises(ValueError, match="workflow project"):
        sample_filter.apply(select(SampleTable))
    assert "workflow_project_id" not in SampleFilter.model_json_schema()["properties"]


def _sample_ids(session: Session, sample_filter: SampleFilter) -> set[UUID]:
    query = sample_filter.apply(select(SampleTable.sample_id))
    return set(session.exec(query).all())
