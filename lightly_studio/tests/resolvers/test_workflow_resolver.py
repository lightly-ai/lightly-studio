"""Tests for workflow_resolver."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from pytest_mock import MockerFixture
from sqlmodel import Session, select

from lightly_studio.models.sample import SampleTable
from lightly_studio.models.workflow import WorkflowStatus
from lightly_studio.resolvers import workflow_resolver
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests import helpers_workflow
from tests.helpers_resolvers import ImageStub, create_collection, create_images


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
