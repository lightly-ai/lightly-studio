"""Tests for workflow_resolver."""

from __future__ import annotations

from collections.abc import Generator
from uuid import UUID

import pytest
import sqlalchemy
from pytest_mock import MockerFixture
from sqlmodel import Session, select

from lightly_studio.models.sample import SampleTable
from lightly_studio.models.workflow import WorkflowStatus
from lightly_studio.resolvers import mcap_group_sequence_resolver, workflow_resolver
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests import helpers_workflow
from tests.helpers_resolvers import ImageStub, create_collection, create_images
from tests.resolvers.mcap_group_sequence_resolver import helpers as mcap_helpers


@pytest.fixture
def workflow_tables(db_session: Session) -> Generator[None, None, None]:
    with helpers_workflow.workflow_tables(session=db_session):
        yield


@pytest.mark.usefixtures("workflow_tables")
def test_get_project_id(db_session: Session) -> None:
    dataset = create_collection(session=db_session, collection_name="dataset")
    other = create_collection(session=db_session, collection_name="other")
    project_id = helpers_workflow.create_project(
        session=db_session, dataset_id=dataset.collection_id
    )

    assert (
        workflow_resolver.get_project_id(session=db_session, dataset_id=dataset.collection_id)
        == project_id
    )
    assert (
        workflow_resolver.get_project_id(session=db_session, dataset_id=other.collection_id) is None
    )


def test_get_project_id__no_workflow_schema(db_session: Session) -> None:
    """Studio without the workflow service has no workflow tables."""
    dataset = create_collection(session=db_session)

    assert (
        workflow_resolver.get_project_id(session=db_session, dataset_id=dataset.collection_id)
        is None
    )


@pytest.mark.usefixtures("workflow_tables")
def test_resolve_sample_filter(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    images = create_images(
        db_session=db_session,
        collection_id=dataset.collection_id,
        images=[ImageStub(path="a.png"), ImageStub(path="b.png")],
    )
    project_id = helpers_workflow.create_project(
        session=db_session, dataset_id=dataset.collection_id
    )
    helpers_workflow.add_batch_files(
        session=db_session, project_id=project_id, states={images[0].sample_id: "rework"}
    )
    filters = ImageFilter(sample_filter=SampleFilter(workflow_states=[WorkflowStatus.REWORK]))

    workflow_resolver.resolve_sample_filter(
        session=db_session, collection_id=dataset.collection_id, filters=filters
    )

    assert filters.sample_filter is not None
    query = filters.sample_filter.apply(select(SampleTable.sample_id))
    assert set(db_session.exec(query).all()) == {images[0].sample_id}


@pytest.mark.parametrize(
    "filters",
    [
        None,
        ImageFilter(),
        ImageFilter(sample_filter=SampleFilter()),
        ImageFilter(sample_filter=SampleFilter(workflow_states=[])),
    ],
)
def test_resolve_sample_filter__no_workflow_states(
    db_session: Session, mocker: MockerFixture, filters: ImageFilter | None
) -> None:
    """Without workflow options, no workflow SQL runs."""
    dataset = create_collection(session=db_session)
    spy = mocker.spy(workflow_resolver, "get_project_id")

    workflow_resolver.resolve_sample_filter(
        session=db_session, collection_id=dataset.collection_id, filters=filters
    )

    spy.assert_not_called()


def _create_dataset_with_states(db_session: Session, states: list[str | None]) -> tuple[UUID, UUID]:
    """Create a dataset with one image per entry, and put the images with a state in a batch.

    Returns:
        The dataset id and its project id.
    """
    dataset = create_collection(session=db_session)
    images = create_images(
        db_session=db_session,
        collection_id=dataset.collection_id,
        images=[ImageStub(path=f"{index}.png") for index in range(len(states))],
    )
    project_id = helpers_workflow.create_project(
        session=db_session, dataset_id=dataset.collection_id
    )
    batched = {image.sample_id: state for image, state in zip(images, states) if state is not None}
    if batched:
        helpers_workflow.add_batch_files(session=db_session, project_id=project_id, states=batched)
    return dataset.collection_id, project_id


@pytest.mark.usefixtures("workflow_tables")
def test_get_status_counts(db_session: Session) -> None:
    dataset_id, project_id = _create_dataset_with_states(
        db_session=db_session,
        states=[None, None, "not_started", "in_progress", "in_progress", "rework", "accepted"],
    )
    # Another project's batch files don't count.
    _create_dataset_with_states(db_session=db_session, states=["in_review", "accepted"])

    counts = workflow_resolver.get_status_counts(
        session=db_session, dataset_id=dataset_id, project_id=project_id
    )

    assert counts == {
        WorkflowStatus.NOT_IN_WORKFLOW: 2,
        WorkflowStatus.NOT_STARTED: 1,
        WorkflowStatus.IN_PROGRESS: 2,
        WorkflowStatus.IN_REVIEW: 0,
        WorkflowStatus.REWORK: 1,
        WorkflowStatus.ACCEPTED: 1,
    }


@pytest.mark.usefixtures("workflow_tables")
def test_get_status_counts__no_batch_files(db_session: Session) -> None:
    dataset_id, project_id = _create_dataset_with_states(db_session=db_session, states=[None, None])

    counts = workflow_resolver.get_status_counts(
        session=db_session, dataset_id=dataset_id, project_id=project_id
    )

    assert counts[WorkflowStatus.NOT_IN_WORKFLOW] == 2
    assert sum(counts.values()) == 2


@pytest.mark.usefixtures("workflow_tables")
def test_get_status_counts__mcap_dataset_counts_sequences_only(db_session: Session) -> None:
    """The groups and MCAP samples of a sequence live in child collections, not the root."""
    batched = mcap_helpers.create_mcap_sequence(session=db_session)
    mcap_helpers.add_mcap_ticks_to_sequence(
        session=db_session, fixture=batched, ticks=[(100, 100), (200, None)]
    )
    dataset_id = batched.sequence_collection.collection_id
    mcap_group_sequence_resolver.create(
        session=db_session, collection_id=dataset_id, recording_id=batched.recording_id
    )
    project_id = helpers_workflow.create_project(session=db_session, dataset_id=dataset_id)
    helpers_workflow.add_batch_files(
        session=db_session, project_id=project_id, states={batched.sample_id: "accepted"}
    )

    counts = workflow_resolver.get_status_counts(
        session=db_session, dataset_id=dataset_id, project_id=project_id
    )

    # Two sequences, one of them batched. The ticks add no samples to the root collection.
    assert counts[WorkflowStatus.ACCEPTED] == 1
    assert counts[WorkflowStatus.NOT_IN_WORKFLOW] == 1
    assert sum(counts.values()) == 2


@pytest.mark.usefixtures("workflow_tables")
def test_get_status_counts__single_query(db_session: Session) -> None:
    dataset_id, project_id = _create_dataset_with_states(
        db_session=db_session, states=[None, "not_started", "in_review", "accepted"]
    )
    statements: list[str] = []

    def listener(*args: object) -> None:
        statements.append(str(args[2]))

    engine = db_session.get_bind()
    sqlalchemy.event.listen(engine, "before_cursor_execute", listener)
    try:
        workflow_resolver.get_status_counts(
            session=db_session, dataset_id=dataset_id, project_id=project_id
        )
    finally:
        sqlalchemy.event.remove(engine, "before_cursor_execute", listener)

    assert len(statements) == 1
