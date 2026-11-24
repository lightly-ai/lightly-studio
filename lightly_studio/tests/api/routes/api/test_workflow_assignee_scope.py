"""A labeler account's workflow grid and its prev/next show only the labeler's own files."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio import deployment
from lightly_studio.api.routes.api.status import HTTP_STATUS_OK
from tests import helpers_resolvers, helpers_workflow

ALL_STATES = ["not_started", "in_progress", "in_review", "rework", "accepted", "not_in_workflow"]
WORKFLOW_FILTER = {"filter_type": "image", "sample_filter": {"workflow_states": ALL_STATES}}
ME = "Me@Example.com"
# Who labels each image, by path; "d" is in no batch.
LABELERS = {"a": "me@example.com", "b": "me@example.com", "c": "other@example.com", "d": None}


@pytest.fixture
def images(db_session: Session) -> Generator[tuple[str, list[str]], None, None]:
    """Images a-d, labeled as in `LABELERS`.

    Yields:
        The collection id and the image sample ids, in path order.
    """
    with helpers_workflow.workflow_tables(session=db_session):
        collection_id = helpers_resolvers.create_collection(session=db_session).collection_id
        samples = [
            helpers_resolvers.create_image(
                session=db_session,
                collection_id=collection_id,
                file_path_abs=f"/images/{name}.png",
            ).sample_id
            for name in LABELERS
        ]
        project_id = helpers_workflow.create_project(session=db_session, dataset_id=collection_id)
        for labeler in {labeler for labeler in LABELERS.values() if labeler}:
            helpers_workflow.add_batch_files(
                session=db_session,
                project_id=project_id,
                states={
                    sample: "in_progress"
                    for sample, (_, owner) in zip(samples, LABELERS.items(), strict=True)
                    if owner == labeler
                },
                labeler=labeler,
                reviewer="rev@example.com",
            )
        yield str(collection_id), [str(sample) for sample in samples]


def _enterprise_headers(mocker: MockerFixture, role: str) -> dict[str, str]:
    """Turn on enterprise mode and return the identity headers of ME with this role."""
    mocker.patch.object(deployment, "is_enterprise", return_value=True)
    return {"X-User-Email": ME, "X-User-Role": role}


def test_images_list__labeler_sees_only_their_files(
    test_client: TestClient, mocker: MockerFixture, images: tuple[str, list[str]]
) -> None:
    collection_id, samples = images

    response = test_client.post(
        f"/api/collections/{collection_id}/images/list",
        headers=_enterprise_headers(mocker=mocker, role="labeler"),
        json={"filters": WORKFLOW_FILTER},
    )

    assert response.status_code == HTTP_STATUS_OK, response.text
    assert [image["sample_id"] for image in response.json()["data"]] == samples[:2]


def test_images_list__editor_sees_everyone(
    test_client: TestClient, mocker: MockerFixture, images: tuple[str, list[str]]
) -> None:
    collection_id, samples = images

    response = test_client.post(
        f"/api/collections/{collection_id}/images/list",
        headers=_enterprise_headers(mocker=mocker, role="editor"),
        json={"filters": WORKFLOW_FILTER},
    )

    assert response.status_code == HTTP_STATUS_OK, response.text
    assert [image["sample_id"] for image in response.json()["data"]] == samples


def test_adjacents__labeler_steps_over_other_files(
    test_client: TestClient, mocker: MockerFixture, images: tuple[str, list[str]]
) -> None:
    collection_id, samples = images

    response = test_client.post(
        f"/api/samples/{samples[1]}/adjacents",
        headers=_enterprise_headers(mocker=mocker, role="labeler"),
        json={"sample_type": "image", "collection_id": collection_id, "filters": WORKFLOW_FILTER},
    )

    assert response.status_code == HTTP_STATUS_OK, response.text
    result = response.json()
    assert result["previous_sample_id"] == samples[0]
    assert result["next_sample_id"] is None
    assert result["total_count"] == 2


@pytest.mark.parametrize("body", [{}, {"filters": {"filter_type": "image"}}])
def test_images_list__labeler_sees_only_their_files_without_status_filter(
    test_client: TestClient,
    mocker: MockerFixture,
    images: tuple[str, list[str]],
    body: dict[str, object],
) -> None:
    collection_id, samples = images

    response = test_client.post(
        f"/api/collections/{collection_id}/images/list",
        headers=_enterprise_headers(mocker=mocker, role="labeler"),
        json=body,
    )

    assert response.status_code == HTTP_STATUS_OK, response.text
    assert [image["sample_id"] for image in response.json()["data"]] == samples[:2]


def test_adjacents__labeler_steps_over_other_files_without_filters(
    test_client: TestClient, mocker: MockerFixture, images: tuple[str, list[str]]
) -> None:
    collection_id, samples = images

    response = test_client.post(
        f"/api/samples/{samples[0]}/adjacents",
        headers=_enterprise_headers(mocker=mocker, role="labeler"),
        json={"sample_type": "image", "collection_id": collection_id},
    )

    assert response.status_code == HTTP_STATUS_OK, response.text
    assert response.json()["next_sample_id"] == samples[1]
    assert response.json()["total_count"] == 2
