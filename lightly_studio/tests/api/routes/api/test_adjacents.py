"""Tests for the adjacents API endpoint."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_OK,
    HTTP_STATUS_UNPROCESSABLE_ENTITY,
)
from tests import helpers_resolvers


def test_get_adjacent_samples__returns_adjacents_for_images(
    db_session: Session,
    test_client: TestClient,
) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    collection_id = collection.collection_id

    image_a = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/a.png",
    )
    image_b = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/b.png",
    )
    image_c = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/c.png",
    )

    response = test_client.post(
        f"/api/samples/{image_b.sample_id}/adjacents",
        json={
            "sample_type": "image",
            "filters": {
                "sample_filter": {"collection_id": str(collection_id)},
            },
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    data = response.json()
    assert data["previous_sample_id"] == str(image_a.sample_id)
    assert data["sample_id"] == str(image_b.sample_id)
    assert data["next_sample_id"] == str(image_c.sample_id)
    assert data["current_sample_position"] == 2
    assert data["total_count"] == 3


def test_get_adjacent_samples__first_sample_has_no_previous(
    db_session: Session,
    test_client: TestClient,
) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    collection_id = collection.collection_id

    image_a = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/a.png",
    )
    image_b = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/b.png",
    )

    response = test_client.post(
        f"/api/samples/{image_a.sample_id}/adjacents",
        json={
            "sample_type": "image",
            "filters": {
                "sample_filter": {"collection_id": str(collection_id)},
            },
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    data = response.json()
    assert data["previous_sample_id"] is None
    assert data["sample_id"] == str(image_a.sample_id)
    assert data["next_sample_id"] == str(image_b.sample_id)
    assert data["current_sample_position"] == 1
    assert data["total_count"] == 2


def test_get_adjacent_samples__last_sample_has_no_next(
    db_session: Session,
    test_client: TestClient,
) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    collection_id = collection.collection_id

    image_a = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/a.png",
    )
    image_b = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/b.png",
    )

    response = test_client.post(
        f"/api/samples/{image_b.sample_id}/adjacents",
        json={
            "sample_type": "image",
            "filters": {
                "sample_filter": {"collection_id": str(collection_id)},
            },
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    data = response.json()
    assert data["previous_sample_id"] == str(image_a.sample_id)
    assert data["sample_id"] == str(image_b.sample_id)
    assert data["next_sample_id"] is None
    assert data["current_sample_position"] == 2
    assert data["total_count"] == 2


def test_get_adjacent_samples__unknown_sample_returns_none(
    db_session: Session,
    test_client: TestClient,
) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    collection_id = collection.collection_id

    helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/a.png",
    )

    unknown_sample_id = uuid4()
    response = test_client.post(
        f"/api/samples/{unknown_sample_id}/adjacents",
        json={
            "sample_type": "image",
            "filters": {
                "sample_filter": {"collection_id": str(collection_id)},
            },
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() is None


def test_get_adjacent_samples__missing_body_returns_unprocessable(
    test_client: TestClient,
) -> None:
    response = test_client.post(
        f"/api/samples/{uuid4()}/adjacents",
        json={},
    )

    assert response.status_code == HTTP_STATUS_UNPROCESSABLE_ENTITY
