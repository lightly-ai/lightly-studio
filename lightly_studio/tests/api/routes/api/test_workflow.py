"""Tests for the workflow API routes."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import HTTP_STATUS_OK
from tests import helpers_resolvers, helpers_workflow


@pytest.fixture
def workflow_tables(db_session: Session) -> Generator[None, None, None]:
    with helpers_workflow.workflow_tables(session=db_session):
        yield


@pytest.mark.usefixtures("workflow_tables")
def test_get_workflow_project(
    db_session: Session,
    test_client: TestClient,
) -> None:
    dataset = helpers_resolvers.create_collection(session=db_session)
    project_id = helpers_workflow.create_project(
        session=db_session, dataset_id=dataset.collection_id
    )

    response = test_client.get(f"/api/collections/{dataset.collection_id}/workflow/project")

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"project_id": str(project_id)}


@pytest.mark.usefixtures("workflow_tables")
def test_get_workflow_project__no_project(
    db_session: Session,
    test_client: TestClient,
) -> None:
    dataset = helpers_resolvers.create_collection(session=db_session)

    response = test_client.get(f"/api/collections/{dataset.collection_id}/workflow/project")

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"project_id": None}


def test_get_workflow_project__no_workflow_tables(
    db_session: Session, test_client: TestClient
) -> None:
    dataset = helpers_resolvers.create_collection(session=db_session)

    response = test_client.get(f"/api/collections/{dataset.collection_id}/workflow/project")

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"project_id": None}
