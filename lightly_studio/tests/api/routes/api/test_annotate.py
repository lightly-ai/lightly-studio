from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_BAD_GATEWAY,
    HTTP_STATUS_NO_CONTENT,
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_OK,
    HTTP_STATUS_SERVICE_UNAVAILABLE,
    HTTP_STATUS_UNPROCESSABLE_ENTITY,
)
from lightly_studio.assisted_labeling.fake_provider import FakeProvider
from lightly_studio.assisted_labeling.provider import ProviderError
from tests.helpers_resolvers import create_collection, create_image
from tests.services.assisted_labeling_service import helpers


def test_get_assisted_labeling_provider(db_session: Session, test_client: TestClient) -> None:
    helpers.select_provider(session=db_session, provider_id="fake")

    response = test_client.get("/api/annotate/provider")

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {
        "provider_id": "fake",
        "display_name": "Fake (offline)",
        "sends_data_to_third_party": False,
        "capabilities": {
            "positive_points": True,
            "negative_points": True,
            "boxes": True,
            "text_prompt": True,
            "max_instances": 3,
        },
        "unavailable_reason": None,
    }


def test_list_assisted_labeling_providers(test_client: TestClient) -> None:
    response = test_client.get("/api/annotate/providers")

    assert response.status_code == HTTP_STATUS_OK
    assert [provider["provider_id"] for provider in response.json()] == [
        "fal_sam3",
        "fal_sam3_1",
        "openai_astra",
        "fake",
    ]


def test_prepare_annotation_image(db_session: Session, test_client: TestClient) -> None:
    helpers.select_provider(session=db_session, provider_id="fake")
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)

    response = test_client.post(
        "/api/annotate/prepare",
        json={"collection_id": str(collection.collection_id), "sample_id": str(image.sample_id)},
    )

    assert response.status_code == HTTP_STATUS_NO_CONTENT


def test_prepare_annotation_image__unavailable(
    db_session: Session, test_client: TestClient, mocker: MockerFixture
) -> None:
    helpers.select_provider(session=db_session, provider_id="fake")
    mocker.patch.object(FakeProvider, "is_available", return_value="Set the API key.")
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)

    response = test_client.post(
        "/api/annotate/prepare",
        json={"collection_id": str(collection.collection_id), "sample_id": str(image.sample_id)},
    )

    assert response.status_code == HTTP_STATUS_SERVICE_UNAVAILABLE
    assert response.json() == {
        "error": "The provider 'Fake (offline)' is not available: Set the API key."
    }


def test_create_interactive_annotation_preview(
    db_session: Session, test_client: TestClient
) -> None:
    helpers.select_provider(session=db_session, provider_id="fake")
    collection = create_collection(session=db_session)
    image = create_image(
        session=db_session, collection_id=collection.collection_id, width=100, height=50
    )

    response = test_client.post(
        "/api/annotate/interactive",
        json={
            "collection_id": str(collection.collection_id),
            "sample_id": str(image.sample_id),
            "points": [{"x": 0.5, "y": 0.5, "positive": True}],
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    prediction = response.json()["prediction"]
    assert prediction["bbox"] == {"x": 45, "y": 20, "width": 11, "height": 11}
    assert prediction["score"] == 0.9
    assert prediction["class_name"] is None


def test_create_interactive_annotation_preview__unknown_sample(
    db_session: Session, test_client: TestClient
) -> None:
    helpers.select_provider(session=db_session, provider_id="fake")
    collection = create_collection(session=db_session)

    response = test_client.post(
        "/api/annotate/interactive",
        json={
            "collection_id": str(collection.collection_id),
            "sample_id": str(uuid4()),
            "points": [{"x": 0.5, "y": 0.5, "positive": True}],
        },
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND


def test_create_interactive_annotation_preview__no_positive_point(
    db_session: Session, test_client: TestClient
) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)

    response = test_client.post(
        "/api/annotate/interactive",
        json={
            "collection_id": str(collection.collection_id),
            "sample_id": str(image.sample_id),
            "points": [{"x": 0.5, "y": 0.5, "positive": False}],
        },
    )

    assert response.status_code == HTTP_STATUS_UNPROCESSABLE_ENTITY


def test_create_interactive_annotation_preview__provider_error(
    db_session: Session, test_client: TestClient, mocker: MockerFixture
) -> None:
    helpers.select_provider(session=db_session, provider_id="fake")
    mocker.patch.object(FakeProvider, "segment", side_effect=ProviderError("Request timed out."))
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)

    response = test_client.post(
        "/api/annotate/interactive",
        json={
            "collection_id": str(collection.collection_id),
            "sample_id": str(image.sample_id),
            "points": [{"x": 0.5, "y": 0.5, "positive": True}],
        },
    )

    assert response.status_code == HTTP_STATUS_BAD_GATEWAY
    assert response.json() == {"error": "Request timed out."}


def test_create_instances_annotation_preview(db_session: Session, test_client: TestClient) -> None:
    helpers.select_provider(session=db_session, provider_id="fake")
    collection = create_collection(session=db_session)
    image = create_image(
        session=db_session, collection_id=collection.collection_id, width=100, height=50
    )

    response = test_client.post(
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
    assert [prediction["bbox"] for prediction in predictions] == [
        {"x": 20, "y": 20, "width": 11, "height": 11},
        {"x": 45, "y": 20, "width": 11, "height": 11},
    ]
    assert [prediction["class_name"] for prediction in predictions] == ["dog", "dog"]


def test_create_instances_annotation_preview__no_prompt(
    db_session: Session, test_client: TestClient
) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)

    response = test_client.post(
        "/api/annotate/instances",
        json={"collection_id": str(collection.collection_id), "sample_id": str(image.sample_id)},
    )

    assert response.status_code == HTTP_STATUS_UNPROCESSABLE_ENTITY
