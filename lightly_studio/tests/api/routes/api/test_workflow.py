"""Tests for the workflow API routes."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import HTTP_STATUS_NOT_FOUND, HTTP_STATUS_OK
from lightly_studio.core.mcap import add_labels
from lightly_studio.core.mcap.type_definitions import SceneUpdateLabels
from lightly_studio.database import db_manager
from tests import helpers_resolvers, helpers_workflow
from tests.core.mcap import helpers as mcap_test_helpers
from tests.export import mcap_helpers


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


@pytest.mark.usefixtures("workflow_tables")
def test_get_workflow_status_counts(
    db_session: Session,
    test_client: TestClient,
) -> None:
    dataset = helpers_resolvers.create_collection(session=db_session)
    images = helpers_resolvers.create_images(
        db_session=db_session,
        collection_id=dataset.collection_id,
        images=[helpers_resolvers.ImageStub(path=f"{index}.png") for index in range(3)],
    )
    project_id = helpers_workflow.create_project(
        session=db_session, dataset_id=dataset.collection_id
    )
    helpers_workflow.add_batch_files(
        session=db_session, project_id=project_id, states={images[0].sample_id: "in_review"}
    )

    response = test_client.get(f"/api/collections/{dataset.collection_id}/workflow/status-counts")

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {
        "counts": {
            "not_in_workflow": 2,
            "not_started": 0,
            "in_progress": 0,
            "in_review": 1,
            "rework": 0,
            "accepted": 0,
        }
    }


def test_get_workflow_status_counts__no_project(
    db_session: Session, test_client: TestClient
) -> None:
    dataset = helpers_resolvers.create_collection(session=db_session)

    response = test_client.get(f"/api/collections/{dataset.collection_id}/workflow/status-counts")

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"counts": None}


def test_count_workflow_objects__sequence_counts_cuboids_on_its_ticks(
    patch_collection: None,  # noqa: ARG001
    test_client: TestClient,
    tmp_path: Path,
) -> None:
    test_client.app.dependency_overrides[db_manager._session_dependency] = (  # type: ignore[attr-defined]
        db_manager.persistent_session
    )
    dataset, sequence, _ = mcap_helpers.index_recording(tmp_path=tmp_path)
    first_ns, second_ns = mcap_test_helpers.LIDAR_LOG_TIMES_NS
    add_labels.write_sequence_labels(
        dataset=dataset,
        sequence=sequence,
        annotation_mcap_uri="memory://ground_truth.mcap",
        messages=[
            (
                first_ns,
                SceneUpdateLabels(
                    cuboids=(
                        mcap_helpers.cuboid(timestamp_ns=first_ns, track_id=1),
                        mcap_helpers.cuboid(timestamp_ns=first_ns, track_id=2),
                    )
                ),
            ),
            (
                second_ns,
                SceneUpdateLabels(
                    cuboids=(mcap_helpers.cuboid(timestamp_ns=second_ns, track_id=1),)
                ),
            ),
        ],
    )
    unknown = uuid4()

    response = test_client.post(
        f"/api/collections/{dataset.collection_id}/workflow/object-counts",
        json={"sample_ids": [str(sequence.sample_id), str(unknown)]},
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"counts": {str(sequence.sample_id): 3, str(unknown): 0}}


def test_count_workflow_objects__unknown_collection(test_client: TestClient) -> None:
    response = test_client.post(
        f"/api/collections/{uuid4()}/workflow/object-counts", json={"sample_ids": []}
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND
