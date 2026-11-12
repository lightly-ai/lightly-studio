from __future__ import annotations

import io

import numpy as np
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from httpx import Response
from PIL import Image as PILImage
from PIL.Image import Image

from lightly_studio_serve import labeling_protocol
from lightly_studio_serve.embedder import TextEmbedder
from lightly_studio_serve.labeling_model import LabelingModel, ModelTask
from lightly_studio_serve.labeling_protocol import PredictionsResponse
from lightly_studio_serve.server import create_app
from lightly_studio_serve.types import EmbeddingResult, EmbeddingSpaceSpec, PredictedAnnotation

WIDTH = 3
HEIGHT = 2


class FakeLabelingModel(LabelingModel):
    """Returns fixed predictions, or raises, and records what it was handed."""

    def __init__(
        self,
        predictions: list[PredictedAnnotation] | None = None,
        error: Exception | None = None,
        ready: bool = True,
    ) -> None:
        self.predictions = predictions or []
        self.error = error
        self.is_ready = ready
        self.received: list[tuple[tuple[int, int], str, float]] = []

    @property
    def model_id(self) -> str:
        return "car-detector"

    @property
    def task(self) -> ModelTask:
        return ModelTask.OBJECT_DETECTION

    @property
    def class_names(self) -> list[str]:
        return ["car"]

    @property
    def ready(self) -> bool:
        return self.is_ready

    def predict(self, image: Image, threshold: float) -> list[PredictedAnnotation]:
        self.received.append((image.size, image.mode, threshold))
        if self.error is not None:
            raise self.error
        return self.predictions


class FakeTextEmbedder(TextEmbedder):
    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        return EmbeddingSpaceSpec(space_key="acme/model@v1", dimension=2)

    def embed_text(self, texts: list[str]) -> EmbeddingResult:
        return EmbeddingResult(
            embeddings=np.zeros((len(texts), 2), dtype=np.float32),
            kept_indices=list(range(len(texts))),
        )


def test_create_app__no_model() -> None:
    with pytest.raises(ValueError, match="Got neither"):
        create_app()


def test_describe_labeling() -> None:
    client = TestClient(create_app(labeling_model=FakeLabelingModel()))

    response = client.get("/v1/labeling/describe")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "protocol_version": "1.0",
        "model_id": "car-detector",
        "task": "object_detection",
        "class_names": ["car"],
        "ready": True,
        "limits": {"max_batch_size": 999, "max_request_bytes": 33554432},
    }


def test_describe__labeling_model_only() -> None:
    client = TestClient(create_app(labeling_model=FakeLabelingModel()))

    assert client.get("/v1/describe").status_code == status.HTTP_404_NOT_FOUND


def test_describe__embedder_and_labeling_model() -> None:
    client = TestClient(create_app(embedder=FakeTextEmbedder(), labeling_model=FakeLabelingModel()))

    assert client.get("/v1/describe").json()["space_key"] == "acme/model@v1"
    assert client.get("/v1/labeling/describe").json()["model_id"] == "car-detector"


def test_predict() -> None:
    mask = np.array([[True, False, False], [False, True, True]], dtype=np.bool_)
    model = FakeLabelingModel(
        predictions=[
            PredictedAnnotation(class_name="car", box=(0.0, 0.0, 3.0, 2.0), score=0.9, mask=mask),
            PredictedAnnotation(class_name="car", box=(1.0, 0.0, 2.0, 1.0), score=0.6),
        ]
    )
    client = TestClient(create_app(labeling_model=model))

    response = _post_predict(client=client, threshold="0.25")

    assert response.status_code == status.HTTP_200_OK
    assert model.received == [((WIDTH, HEIGHT), "RGB", 0.25)]
    body = PredictionsResponse.model_validate(response.json())
    assert body.model_id == "car-detector"
    first, second = (
        labeling_protocol.from_wire_prediction(prediction=prediction)
        for prediction in body.predictions
    )
    assert (first.class_name, first.box, first.score) == ("car", (0.0, 0.0, 3.0, 2.0), 0.9)
    assert first.mask is not None
    np.testing.assert_array_equal(first.mask, mask)
    assert second == PredictedAnnotation(class_name="car", box=(1.0, 0.0, 2.0, 1.0), score=0.6)


def test_predict__wrong_token() -> None:
    model = FakeLabelingModel()
    client = TestClient(create_app(labeling_model=model, api_key="secret"))

    response = _post_predict(client=client, threshold="0.5", token="wrong")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert model.received == []
    assert _post_predict(client=client, threshold="0.5", token="secret").status_code == (
        status.HTTP_200_OK
    )


def test_predict__not_ready() -> None:
    model = FakeLabelingModel(ready=False)
    client = TestClient(create_app(labeling_model=model))

    response = _post_predict(client=client, threshold="0.5")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert model.received == []
    describe = client.get("/v1/labeling/describe")
    assert describe.status_code == status.HTTP_200_OK
    assert describe.json()["ready"] is False


def test_predict__not_an_image() -> None:
    model = FakeLabelingModel()
    client = TestClient(create_app(labeling_model=model))

    response = _post_predict(client=client, threshold="0.5", image=b"not an image")

    assert response.status_code == 422
    assert response.json() == {"detail": "The image cannot be decoded."}
    assert model.received == []


@pytest.mark.parametrize("threshold", ["1.5", "-0.1", "nan", "high"])
def test_predict__invalid_threshold(threshold: str) -> None:
    model = FakeLabelingModel()
    client = TestClient(create_app(labeling_model=model))

    response = _post_predict(client=client, threshold=threshold)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert model.received == []


def test_predict__model_error() -> None:
    model = FakeLabelingModel(error=RuntimeError("The model names its input."))
    client = TestClient(create_app(labeling_model=model), raise_server_exceptions=False)

    response = _post_predict(client=client, threshold="0.5")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {
        "detail": "The labeling model raised RuntimeError. See the server log."
    }


def test_predict__invalid_prediction() -> None:
    model = FakeLabelingModel(
        predictions=[
            PredictedAnnotation(
                class_name="car",
                box=(0.0, 0.0, 3.0, 2.0),
                score=0.9,
                mask=np.ones((HEIGHT, WIDTH), dtype=np.float32),
            )
        ]
    )
    client = TestClient(create_app(labeling_model=model), raise_server_exceptions=False)

    response = _post_predict(client=client, threshold="0.5")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {
        "detail": "The labeling model returned a prediction that is not valid: "
        "The mask is not a boolean array with two dimensions."
    }


def _png_bytes() -> bytes:
    buffer = io.BytesIO()
    PILImage.new(mode="RGB", size=(WIDTH, HEIGHT)).save(buffer, format="PNG")
    return buffer.getvalue()


def _post_predict(
    client: TestClient, threshold: str, image: bytes | None = None, token: str | None = None
) -> Response:
    response: Response = client.post(
        "/v1/labeling/predict",
        files={"image": ("image.png", _png_bytes() if image is None else image)},
        data={"threshold": threshold},
        headers={} if token is None else {"Authorization": f"Bearer {token}"},
    )
    return response
