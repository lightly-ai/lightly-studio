from __future__ import annotations

import importlib.util
import threading
import uuid
from typing import Any
from uuid import UUID

import numpy as np
import pytest
from fastapi.testclient import TestClient
from httpx import Response
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_BAD_GATEWAY,
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_OK,
    HTTP_STATUS_SERVICE_UNAVAILABLE,
    HTTP_STATUS_UNPROCESSABLE_ENTITY,
)
from lightly_studio.assisted_labeling import fal_sam3_provider
from lightly_studio.assisted_labeling.fal_sam3_provider import FalSam3Provider
from lightly_studio.assisted_labeling.provider import Prediction, ProviderError
from tests.helpers_resolvers import create_collection, create_image
from tests.services.assisted_labeling_service.helpers import StubProvider

POSITIVE_POINT = {"x": 0.5, "y": 0.5, "positive": True}


@pytest.fixture
def stub_provider(mocker: MockerFixture) -> StubProvider:
    provider = StubProvider()
    mocker.patch.object(fal_sam3_provider, "get_provider", return_value=provider)
    return provider


def test_get_assisted_labeling_status(
    test_client: TestClient, mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAL_KEY", "secret")
    mocker.patch.object(importlib.util, "find_spec", return_value=mocker.sentinel.spec)

    response = test_client.get("/api/annotate/status")

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"unavailable_reason": None}


def test_get_assisted_labeling_status__without_key(
    test_client: TestClient, mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("FAL_KEY", raising=False)
    mocker.patch.object(importlib.util, "find_spec", return_value=mocker.sentinel.spec)

    response = test_client.get("/api/annotate/status")

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"unavailable_reason": "Set the FAL_KEY environment variable."}


def test_get_assisted_labeling_status__without_extra(
    test_client: TestClient, mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAL_KEY", "secret")
    mocker.patch.object(importlib.util, "find_spec", return_value=None)

    response = test_client.get("/api/annotate/status")

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {
        "unavailable_reason": 'Install the fal extra: pip install "lightly-studio[fal]".'
    }


def test_create_interactive_annotation_preview(
    db_session: Session, media_test_client: TestClient, stub_provider: StubProvider
) -> None:
    mask = np.zeros((50, 100), dtype=np.bool_)
    mask[20:31, 45:56] = True
    stub_provider.predictions = [Prediction(mask=mask, score=0.9)]
    collection = create_collection(session=db_session)
    image = create_image(
        session=db_session, collection_id=collection.collection_id, width=100, height=50
    )

    response = _post_interactive(
        client=media_test_client, collection_id=collection.collection_id, sample_id=image.sample_id
    )

    assert response.status_code == HTTP_STATUS_OK
    prediction = response.json()["prediction"]
    assert prediction["bbox"] == {"x": 45, "y": 20, "width": 11, "height": 11}
    assert prediction["score"] == 0.9


def test_create_interactive_annotation_preview__provider_thread(
    db_session: Session,
    media_test_client: TestClient,
    mocker: MockerFixture,
    stub_provider: StubProvider,
) -> None:
    thread_names: list[str] = []

    def segment(*_args: Any, **_kwargs: Any) -> list[Prediction]:
        thread_names.append(threading.current_thread().name)
        return []

    mocker.patch.object(stub_provider, "segment", side_effect=segment)
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)

    response = _post_interactive(
        client=media_test_client, collection_id=collection.collection_id, sample_id=image.sample_id
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

    response = _post_interactive(
        client=media_test_client,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        boxes=[{"x": 0.1, "y": 0.2, "width": 0.4, "height": 0.6}],
    )

    assert response.status_code == HTTP_STATUS_UNPROCESSABLE_ENTITY


def test_create_interactive_annotation_preview__other_collection(
    db_session: Session, media_test_client: TestClient, stub_provider: StubProvider
) -> None:
    collection = create_collection(session=db_session, collection_name="first")
    other_collection = create_collection(session=db_session, collection_name="second")
    image = create_image(session=db_session, collection_id=other_collection.collection_id)

    response = _post_interactive(
        client=media_test_client, collection_id=collection.collection_id, sample_id=image.sample_id
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND
    assert stub_provider.prompts == []


def test_create_interactive_annotation_preview__unknown_sample(
    db_session: Session, media_test_client: TestClient, stub_provider: StubProvider
) -> None:
    collection = create_collection(session=db_session)

    response = _post_interactive(
        client=media_test_client, collection_id=collection.collection_id, sample_id=uuid.uuid4()
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND
    assert stub_provider.prompts == []


def test_create_interactive_annotation_preview__unknown_image_size(
    db_session: Session, media_test_client: TestClient, stub_provider: StubProvider
) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id, width=0)

    response = _post_interactive(
        client=media_test_client, collection_id=collection.collection_id, sample_id=image.sample_id
    )

    assert response.status_code == HTTP_STATUS_UNPROCESSABLE_ENTITY
    assert response.json() == {"error": f"Image {image.sample_id} has no known size."}
    assert stub_provider.prompts == []


def test_create_interactive_annotation_preview__provider_error(
    db_session: Session, media_test_client: TestClient, stub_provider: StubProvider
) -> None:
    stub_provider.error = ProviderError("Request timed out.")
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)

    response = _post_interactive(
        client=media_test_client, collection_id=collection.collection_id, sample_id=image.sample_id
    )

    assert response.status_code == HTTP_STATUS_BAD_GATEWAY
    assert response.json() == {"error": "Request timed out."}


def test_create_interactive_annotation_preview__unavailable(
    db_session: Session,
    media_test_client: TestClient,
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FAL_KEY", raising=False)
    mocker.patch.object(importlib.util, "find_spec", return_value=mocker.sentinel.spec)
    create_client = mocker.patch.object(fal_sam3_provider, "_create_client")
    mocker.patch.object(fal_sam3_provider, "get_provider", return_value=FalSam3Provider())
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)

    response = _post_interactive(
        client=media_test_client, collection_id=collection.collection_id, sample_id=image.sample_id
    )

    assert response.status_code == HTTP_STATUS_SERVICE_UNAVAILABLE
    assert response.json() == {"error": "Set the FAL_KEY environment variable."}
    create_client.assert_not_called()


def _post_interactive(
    client: TestClient,
    collection_id: UUID,
    sample_id: UUID,
    boxes: list[dict[str, float]] | None = None,
) -> Response:
    return client.post(
        "/api/annotate/interactive",
        json={
            "collection_id": str(collection_id),
            "sample_id": str(sample_id),
            "points": [POSITIVE_POINT],
            "boxes": boxes,
        },
    )
