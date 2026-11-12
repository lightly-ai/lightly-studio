from __future__ import annotations

import threading
import uuid
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from lightly_studio_serve import server
from lightly_studio_serve.labeling import LabelingModel, ModelTask, PredictedAnnotation
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_BAD_GATEWAY,
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_OK,
    HTTP_STATUS_SERVICE_UNAVAILABLE,
    HTTP_STATUS_UNPROCESSABLE_ENTITY,
)
from lightly_studio.assisted_labeling import labeling_model_registry, remote_runner_cache
from lightly_studio.assisted_labeling.labeling_model_registry import LabelingModelRegistry
from lightly_studio.assisted_labeling.remote_runner_cache import RemoteRunnerCache
from lightly_studio.embed.remote import connection
from lightly_studio.models.image import ImageTable
from lightly_studio.models.labeling_model import LabelingModelCreate
from lightly_studio.resolvers import labeling_model_resolver
from tests.assisted_labeling import helpers
from tests.assisted_labeling.helpers import StubLabelingModel
from tests.helpers_resolvers import create_collection, create_image


class _TaskRaisesModel(StubLabelingModel):
    @property
    def task(self) -> ModelTask:
        raise RuntimeError("The model config is missing.")


@pytest.fixture
def model_registry(mocker: MockerFixture) -> LabelingModelRegistry:
    registry = LabelingModelRegistry()
    mocker.patch.object(labeling_model_registry, "_registry", registry)
    return registry


def test_get_labeling_models(
    media_test_client: TestClient, model_registry: LabelingModelRegistry, db_session: Session
) -> None:
    model_registry.register(
        model=StubLabelingModel(
            model_id="seg", task=ModelTask.INSTANCE_SEGMENTATION, class_names=["cat"]
        )
    )

    collection = create_collection(session=db_session)
    response = media_test_client.get(
        "/api/annotate/models", params={"collection_id": str(collection.collection_id)}
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {
        "models": [{"id": "seg", "task": "instance_segmentation", "class_names": ["cat"]}],
        "has_loading_models": False,
    }


@pytest.mark.usefixtures("model_registry")
def test_get_labeling_models__none_registered(
    media_test_client: TestClient, db_session: Session
) -> None:
    collection = create_collection(session=db_session)
    response = media_test_client.get(
        "/api/annotate/models", params={"collection_id": str(collection.collection_id)}
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"models": [], "has_loading_models": False}


def test_get_labeling_models__not_ready(
    media_test_client: TestClient, model_registry: LabelingModelRegistry, db_session: Session
) -> None:
    loading_model = StubLabelingModel(model_id="loading")
    loading_model.is_ready = False
    model_registry.register(model=loading_model)
    model_registry.register(model=StubLabelingModel(model_id="loaded"))

    collection = create_collection(session=db_session)
    response = media_test_client.get(
        "/api/annotate/models", params={"collection_id": str(collection.collection_id)}
    )

    assert response.status_code == HTTP_STATUS_OK
    assert [model["id"] for model in response.json()["models"]] == ["loaded"]
    assert response.json()["has_loading_models"]


def test_get_labeling_models__ready_during_request(
    media_test_client: TestClient, model_registry: LabelingModelRegistry, db_session: Session
) -> None:
    model_registry.register(model=helpers.ReadyOnSecondReadModel(model_id="late"))

    collection = create_collection(session=db_session)
    response = media_test_client.get(
        "/api/annotate/models", params={"collection_id": str(collection.collection_id)}
    )

    assert response.status_code == HTTP_STATUS_OK
    # The model is either in the list or counted as loading, so the GUI polls for it.
    assert response.json() == {"models": [], "has_loading_models": True}


def test_get_labeling_models__faulty_model(
    media_test_client: TestClient, model_registry: LabelingModelRegistry, db_session: Session
) -> None:
    model_registry.register(model=_TaskRaisesModel(model_id="faulty"))
    model_registry.register(model=StubLabelingModel(model_id="working"))

    collection = create_collection(session=db_session)
    response = media_test_client.get(
        "/api/annotate/models", params={"collection_id": str(collection.collection_id)}
    )

    assert response.status_code == HTTP_STATUS_OK
    assert [model["id"] for model in response.json()["models"]] == ["working"]


def test_create_model_annotation_preview(
    db_session: Session,
    media_test_client: TestClient,
    model_registry: LabelingModelRegistry,
    tmp_path: Path,
) -> None:
    model = StubLabelingModel(
        model_id="ltdetrv2-s-coco",
        class_names=["cat"],
        predictions=[PredictedAnnotation(class_name="cat", box=(10.0, 5.0, 30.0, 25.0), score=0.8)],
    )
    model_registry.register(model=model)
    collection = create_collection(session=db_session)
    image = _create_png_image(
        session=db_session,
        collection_id=collection.collection_id,
        tmp_path=tmp_path,
        width=100,
        height=50,
    )

    response = media_test_client.post(
        "/api/annotate/models/predict",
        json={
            "collection_id": str(collection.collection_id),
            "sample_id": str(image.sample_id),
            "model_id": "ltdetrv2-s-coco",
            "threshold": 0.3,
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    assert model.thresholds == [0.3]
    assert [pil_image.size for pil_image in model.images] == [(100, 50)]
    assert response.json() == {
        "predictions": [
            {
                "class_name": "cat",
                "bbox": {"x": 10, "y": 5, "width": 20, "height": 20},
                "segmentation_mask": None,
                "score": 0.8,
            }
        ]
    }


def test_create_model_annotation_preview__unknown_model(
    db_session: Session, media_test_client: TestClient, model_registry: LabelingModelRegistry
) -> None:
    model_registry.register(model=StubLabelingModel(model_id="other"))
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)

    response = _post_model_preview(
        client=media_test_client,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        model_id="m",
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND
    assert response.json() == {"error": "No labeling model with ID 'm' is registered."}


def test_create_model_annotation_preview__not_ready(
    db_session: Session, media_test_client: TestClient, model_registry: LabelingModelRegistry
) -> None:
    model = StubLabelingModel(model_id="m")
    model.is_ready = False
    model_registry.register(model=model)
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)

    response = _post_model_preview(
        client=media_test_client,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        model_id="m",
    )

    assert response.status_code == HTTP_STATUS_SERVICE_UNAVAILABLE
    assert response.json() == {"error": "The labeling model 'm' is still loading. Try again later."}
    assert model.thresholds == []


def test_create_model_annotation_preview__model_error(
    db_session: Session,
    media_test_client: TestClient,
    model_registry: LabelingModelRegistry,
    tmp_path: Path,
) -> None:
    model_registry.register(model=StubLabelingModel(model_id="m", error=RuntimeError("boom")))
    collection = create_collection(session=db_session)
    image = _create_png_image(
        session=db_session,
        collection_id=collection.collection_id,
        tmp_path=tmp_path,
        width=100,
        height=50,
    )

    response = _post_model_preview(
        client=media_test_client,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        model_id="m",
    )

    assert response.status_code == HTTP_STATUS_BAD_GATEWAY
    assert response.json() == {
        "error": "The labeling model 'm' raised RuntimeError. See the server log."
    }


def test_create_model_annotation_preview__invalid_threshold(
    test_client: TestClient, model_registry: LabelingModelRegistry
) -> None:
    model = StubLabelingModel(model_id="m")
    model_registry.register(model=model)

    response = test_client.post(
        "/api/annotate/models/predict",
        json={
            "collection_id": str(uuid.uuid4()),
            "sample_id": str(uuid.uuid4()),
            "model_id": "m",
            "threshold": 1.5,
        },
    )

    assert response.status_code == HTTP_STATUS_UNPROCESSABLE_ENTITY
    assert model.thresholds == []


def test_create_model_annotation_preview__predict_thread(
    db_session: Session,
    media_test_client: TestClient,
    model_registry: LabelingModelRegistry,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    thread_names: list[str] = []

    def predict(*_args: Any, **_kwargs: Any) -> list[PredictedAnnotation]:
        thread_names.append(threading.current_thread().name)
        return []

    model = StubLabelingModel(model_id="m")
    mocker.patch.object(model, "predict", side_effect=predict)
    model_registry.register(model=model)
    collection = create_collection(session=db_session)
    image = _create_png_image(
        session=db_session,
        collection_id=collection.collection_id,
        tmp_path=tmp_path,
        width=100,
        height=50,
    )

    response = _post_model_preview(
        client=media_test_client,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        model_id="m",
    )

    assert response.status_code == HTTP_STATUS_OK
    assert len(thread_names) == 1
    assert thread_names[0].startswith("labeling_model")


def test_create_model_annotation_preview__unknown_sample(
    db_session: Session, media_test_client: TestClient, model_registry: LabelingModelRegistry
) -> None:
    model = StubLabelingModel(model_id="m")
    model_registry.register(model=model)
    collection = create_collection(session=db_session)

    response = _post_model_preview(
        client=media_test_client,
        collection_id=collection.collection_id,
        sample_id=uuid.uuid4(),
        model_id="m",
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND
    assert model.thresholds == []


def test_create_model_annotation_preview__image_not_decodable(
    db_session: Session,
    media_test_client: TestClient,
    model_registry: LabelingModelRegistry,
    tmp_path: Path,
) -> None:
    model = StubLabelingModel(model_id="m")
    model_registry.register(model=model)
    collection = create_collection(session=db_session)
    file_path = tmp_path / "image.png"
    file_path.write_bytes(b"not an image")
    image = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs=str(file_path),
        width=100,
        height=50,
    )

    response = _post_model_preview(
        client=media_test_client,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        model_id="m",
    )

    assert response.status_code == HTTP_STATUS_BAD_GATEWAY
    assert response.json() == {"error": "The image file 'image.png' cannot be decoded."}
    assert model.thresholds == []


def test_create_model_annotation_preview__undeclared_class(
    db_session: Session,
    media_test_client: TestClient,
    model_registry: LabelingModelRegistry,
    tmp_path: Path,
) -> None:
    model = StubLabelingModel(
        model_id="m",
        class_names=["cat"],
        predictions=[PredictedAnnotation(class_name="dog", box=(10.0, 5.0, 30.0, 25.0), score=0.8)],
    )
    model_registry.register(model=model)
    collection = create_collection(session=db_session)
    image = _create_png_image(
        session=db_session,
        collection_id=collection.collection_id,
        tmp_path=tmp_path,
        width=100,
        height=50,
    )

    response = _post_model_preview(
        client=media_test_client,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        model_id="m",
    )

    assert response.status_code == HTTP_STATUS_BAD_GATEWAY
    assert "not one of its annotation classes" in response.json()["error"]


def _create_png_image(
    session: Session, collection_id: UUID, tmp_path: Path, width: int, height: int
) -> ImageTable:
    """Create an image sample with a PNG file on disk."""
    file_path = tmp_path / "image.png"
    file_path.write_bytes(helpers.png_bytes(width=width, height=height))
    return create_image(
        session=session,
        collection_id=collection_id,
        file_path_abs=str(file_path),
        width=width,
        height=height,
    )


def _post_model_preview(
    client: TestClient, collection_id: UUID, sample_id: UUID, model_id: str
) -> Response:
    response: Response = client.post(
        "/api/annotate/models/predict",
        json={
            "collection_id": str(collection_id),
            "sample_id": str(sample_id),
            "model_id": model_id,
        },
    )
    return response


@pytest.mark.usefixtures("model_registry")
def test_get_labeling_models__unknown_collection(media_test_client: TestClient) -> None:
    response = media_test_client.get(
        "/api/annotate/models", params={"collection_id": str(uuid.UUID(int=5))}
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND


@pytest.mark.usefixtures("model_registry")
def test_get_labeling_models__saved_server(
    db_session: Session, media_test_client: TestClient, mocker: MockerFixture
) -> None:
    _serve_labeling_model(
        mocker=mocker,
        model=StubLabelingModel(model_id="remote-detector", class_names=["car"]),
    )
    collection = create_collection(session=db_session)
    other_collection = create_collection(session=db_session, collection_name="other")
    _save_server(session=db_session, dataset_id=collection.dataset_id, model_id="remote-detector")

    response = media_test_client.get(
        "/api/annotate/models", params={"collection_id": str(collection.collection_id)}
    )
    other_response = media_test_client.get(
        "/api/annotate/models", params={"collection_id": str(other_collection.collection_id)}
    )

    assert response.json() == {
        "models": [{"id": "remote-detector", "task": "object_detection", "class_names": ["car"]}],
        "has_loading_models": False,
    }
    assert other_response.json() == {"models": [], "has_loading_models": False}


@pytest.mark.usefixtures("model_registry")
def test_create_model_annotation_preview__saved_server(
    db_session: Session, media_test_client: TestClient, mocker: MockerFixture, tmp_path: Path
) -> None:
    model = StubLabelingModel(
        model_id="remote-detector",
        class_names=["car"],
        predictions=[PredictedAnnotation(class_name="car", box=(10.0, 5.0, 30.0, 25.0), score=0.8)],
    )
    _serve_labeling_model(mocker=mocker, model=model)
    collection = create_collection(session=db_session)
    _save_server(session=db_session, dataset_id=collection.dataset_id, model_id="remote-detector")
    image = _create_png_image(
        session=db_session,
        collection_id=collection.collection_id,
        tmp_path=tmp_path,
        width=100,
        height=50,
    )

    response = media_test_client.post(
        "/api/annotate/models/predict",
        json={
            "collection_id": str(collection.collection_id),
            "sample_id": str(image.sample_id),
            "model_id": "remote-detector",
            "threshold": 0.3,
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    assert model.thresholds == [0.3]
    assert [pil_image.size for pil_image in model.images] == [(100, 50)]
    assert response.json() == {
        "predictions": [
            {
                "class_name": "car",
                "bbox": {"x": 10, "y": 5, "width": 20, "height": 20},
                "segmentation_mask": None,
                "score": 0.8,
            }
        ]
    }


def _serve_labeling_model(mocker: MockerFixture, model: LabelingModel) -> None:
    """Serve ``model`` to every client that opens, and start with an empty runner cache."""
    mocker.patch.object(remote_runner_cache, "_cache", RemoteRunnerCache())
    mocker.patch.object(
        connection,
        "build_client",
        side_effect=lambda url: TestClient(
            server.create_app(labeling_model=model), base_url=url, follow_redirects=False
        ),
    )


def _save_server(session: Session, dataset_id: UUID, model_id: str) -> None:
    labeling_model_resolver.set_remote(
        session=session,
        labeling_model=LabelingModelCreate(
            dataset_id=dataset_id, model_id=model_id, url="https://labeling.test"
        ),
    )
