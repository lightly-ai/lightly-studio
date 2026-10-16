from __future__ import annotations

import threading
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_BAD_GATEWAY,
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_OK,
    HTTP_STATUS_SERVICE_UNAVAILABLE,
    HTTP_STATUS_UNPROCESSABLE_ENTITY,
)
from lightly_studio.assisted_labeling import provider_ids
from lightly_studio.assisted_labeling.fake_provider import FakeProvider
from lightly_studio.assisted_labeling.provider import Prediction, ProviderError
from tests.helpers_resolvers import create_collection, create_image
from tests.services.assisted_labeling_service import helpers

POSITIVE_POINT = {"x": 0.5, "y": 0.5, "positive": True}


def test_list_providers(test_client: TestClient) -> None:
    response = test_client.get("/api/annotate/providers")

    assert response.status_code == HTTP_STATUS_OK
    providers = response.json()
    by_id = {provider["provider_id"]: provider for provider in providers}
    assert provider_ids.FAKE_PROVIDER_ID in by_id
    assert provider_ids.FAL_SAM3_PROVIDER_ID in by_id
    fake = by_id[provider_ids.FAKE_PROVIDER_ID]
    assert fake["capabilities"] == FakeProvider().capabilities().model_dump()
    assert fake["unavailable_reason"] is None


def test_create_interactive_annotation_preview(
    db_session: Session, media_test_client: TestClient
) -> None:
    helpers.select_provider(session=db_session, provider_id=provider_ids.FAKE_PROVIDER_ID)
    collection = create_collection(session=db_session)
    image = create_image(
        session=db_session, collection_id=collection.collection_id, width=100, height=50
    )

    response = media_test_client.post(
        "/api/annotate/interactive",
        json={
            "collection_id": str(collection.collection_id),
            "sample_id": str(image.sample_id),
            "points": [POSITIVE_POINT],
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    prediction = response.json()["prediction"]
    # The fake provider returns a disk with radius 5 around the pixel (50, 25).
    assert prediction["bbox"] == {"x": 45, "y": 20, "width": 11, "height": 11}
    assert prediction["score"] == 0.9
    assert prediction["class_name"] is None


def test_create_interactive_annotation_preview__provider_thread(
    db_session: Session, media_test_client: TestClient, mocker: MockerFixture
) -> None:
    helpers.select_provider(session=db_session, provider_id=provider_ids.FAKE_PROVIDER_ID)
    thread_names: list[str] = []

    def segment(*_args: Any, **_kwargs: Any) -> list[Prediction]:
        thread_names.append(threading.current_thread().name)
        return []

    mocker.patch.object(FakeProvider, "segment", side_effect=segment)
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)

    response = media_test_client.post(
        "/api/annotate/interactive",
        json={
            "collection_id": str(collection.collection_id),
            "sample_id": str(image.sample_id),
            "points": [POSITIVE_POINT],
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"prediction": None}
    assert len(thread_names) == 1
    assert thread_names[0].startswith("assisted_labeling")


def test_create_interactive_annotation_preview__points_and_boxes(
    db_session: Session, media_test_client: TestClient
) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)

    response = media_test_client.post(
        "/api/annotate/interactive",
        json={
            "collection_id": str(collection.collection_id),
            "sample_id": str(image.sample_id),
            "points": [POSITIVE_POINT],
            "boxes": [{"x": 0.1, "y": 0.2, "width": 0.4, "height": 0.6}],
        },
    )

    assert response.status_code == HTTP_STATUS_UNPROCESSABLE_ENTITY


def test_create_interactive_annotation_preview__no_positive_point(
    db_session: Session, media_test_client: TestClient
) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)

    response = media_test_client.post(
        "/api/annotate/interactive",
        json={
            "collection_id": str(collection.collection_id),
            "sample_id": str(image.sample_id),
            "points": [{"x": 0.5, "y": 0.5, "positive": False}],
        },
    )

    assert response.status_code == HTTP_STATUS_UNPROCESSABLE_ENTITY


def test_create_interactive_annotation_preview__other_collection(
    db_session: Session, media_test_client: TestClient
) -> None:
    helpers.select_provider(session=db_session, provider_id=provider_ids.FAKE_PROVIDER_ID)
    collection = create_collection(session=db_session, collection_name="first")
    other_collection = create_collection(session=db_session, collection_name="second")
    image = create_image(session=db_session, collection_id=other_collection.collection_id)

    response = media_test_client.post(
        "/api/annotate/interactive",
        json={
            "collection_id": str(collection.collection_id),
            "sample_id": str(image.sample_id),
            "points": [POSITIVE_POINT],
        },
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND


def test_create_interactive_annotation_preview__unknown_sample(
    db_session: Session, media_test_client: TestClient
) -> None:
    helpers.select_provider(session=db_session, provider_id=provider_ids.FAKE_PROVIDER_ID)
    collection = create_collection(session=db_session)

    response = media_test_client.post(
        "/api/annotate/interactive",
        json={
            "collection_id": str(collection.collection_id),
            "sample_id": str(uuid4()),
            "points": [POSITIVE_POINT],
        },
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND


def test_create_interactive_annotation_preview__provider_error(
    db_session: Session, media_test_client: TestClient, mocker: MockerFixture
) -> None:
    helpers.select_provider(session=db_session, provider_id=provider_ids.FAKE_PROVIDER_ID)
    mocker.patch.object(FakeProvider, "segment", side_effect=ProviderError("Request timed out."))
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)

    response = media_test_client.post(
        "/api/annotate/interactive",
        json={
            "collection_id": str(collection.collection_id),
            "sample_id": str(image.sample_id),
            "points": [POSITIVE_POINT],
        },
    )

    assert response.status_code == HTTP_STATUS_BAD_GATEWAY
    assert response.json() == {"error": "Request timed out."}


def test_create_interactive_annotation_preview__unavailable(
    db_session: Session, media_test_client: TestClient, mocker: MockerFixture
) -> None:
    helpers.select_provider(session=db_session, provider_id=provider_ids.FAKE_PROVIDER_ID)
    mocker.patch.object(FakeProvider, "is_available", return_value="Set the API key.")
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)

    response = media_test_client.post(
        "/api/annotate/interactive",
        json={
            "collection_id": str(collection.collection_id),
            "sample_id": str(image.sample_id),
            "points": [POSITIVE_POINT],
        },
    )

    assert response.status_code == HTTP_STATUS_SERVICE_UNAVAILABLE
    assert response.json() == {
        "error": "The provider 'Fake (offline)' is not available: Set the API key."
    }


def test_create_instances_annotation_preview(
    db_session: Session, media_test_client: TestClient
) -> None:
    helpers.select_provider(session=db_session, provider_id=provider_ids.FAKE_PROVIDER_ID)
    collection = create_collection(session=db_session)
    image = create_image(
        session=db_session, collection_id=collection.collection_id, width=100, height=50
    )

    response = media_test_client.post(
        "/api/annotate/instances",
        json={
            "collection_id": str(collection.collection_id),
            "sample_id": str(image.sample_id),
            "prompt": "dog",
            "max_instances": 2,
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    predictions = response.json()["predictions"]
    assert [prediction["bbox"]["x"] for prediction in predictions] == [20, 45]
    assert [prediction["class_name"] for prediction in predictions] == ["dog", "dog"]


def test_create_instances_annotation_preview__blank_prompt(
    db_session: Session, media_test_client: TestClient
) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)

    response = media_test_client.post(
        "/api/annotate/instances",
        json={
            "collection_id": str(collection.collection_id),
            "sample_id": str(image.sample_id),
            "prompt": "  ",
        },
    )

    assert response.status_code == HTTP_STATUS_UNPROCESSABLE_ENTITY


def test_create_instances_annotation_preview__too_many_instances(
    db_session: Session, media_test_client: TestClient
) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)

    response = media_test_client.post(
        "/api/annotate/instances",
        json={
            "collection_id": str(collection.collection_id),
            "sample_id": str(image.sample_id),
            "prompt": "dog",
            "max_instances": 33,
        },
    )

    assert response.status_code == HTTP_STATUS_UNPROCESSABLE_ENTITY
