from __future__ import annotations

import io

import numpy as np
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from httpx import Response
from PIL import Image as PILImage
from PIL.Image import Image

from lightly_studio_serve import labeling_protocol, server
from lightly_studio_serve.labeling import PredictedAnnotation
from lightly_studio_serve.labeling_protocol import PredictionsResponse
from tests.labeling.helpers import FakeLabelingModel

WIDTH = 3
HEIGHT = 2


def test_describe_labeling() -> None:
    model = FakeLabelingModel(model_id="car-detector", class_names=["car"])
    client = TestClient(server.create_app(labeling_model=model))

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


def test_describe_labeling__empty_model_id() -> None:
    model = FakeLabelingModel(model_id="")
    client = TestClient(server.create_app(labeling_model=model), raise_server_exceptions=False)

    response = client.get("/v1/labeling/describe")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {
        "detail": "The labeling model has a property that is not valid: "
        "model_id: String should have at least 1 character"
    }


def test_predict() -> None:
    mask = np.array([[True, False, False], [False, True, True]], dtype=np.bool_)
    model = FakeLabelingModel(
        predictions=[
            PredictedAnnotation(class_name="car", box=(0.0, 0.0, 3.0, 2.0), score=0.9, mask=mask),
            PredictedAnnotation(class_name="car", box=(1.0, 0.0, 2.0, 1.0), score=0.6),
        ],
        model_id="car-detector",
        class_names=["car"],
    )
    client = TestClient(server.create_app(labeling_model=model))

    response = _post_predict(client=client, threshold="0.25")

    assert response.status_code == status.HTTP_200_OK
    assert model.received == [((WIDTH, HEIGHT), "RGB", 0.25)]
    body = PredictionsResponse.model_validate(response.json())
    assert body.model_id == "car-detector"
    first, second = (
        labeling_protocol.from_wire_prediction(prediction=prediction, width=WIDTH, height=HEIGHT)
        for prediction in body.predictions
    )
    assert (first.class_name, first.box, first.score) == ("car", (0.0, 0.0, 3.0, 2.0), 0.9)
    assert first.mask is not None
    np.testing.assert_array_equal(first.mask, mask)
    assert second == PredictedAnnotation(class_name="car", box=(1.0, 0.0, 2.0, 1.0), score=0.6)


def test_predict__wrong_token() -> None:
    model = FakeLabelingModel()
    client = TestClient(server.create_app(labeling_model=model, api_key="secret"))

    response = _post_predict(client=client, threshold="0.5", token="wrong")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert model.received == []
    assert _post_predict(client=client, threshold="0.5", token="secret").status_code == (
        status.HTTP_200_OK
    )


def test_predict__not_ready() -> None:
    model = FakeLabelingModel(ready=False)
    client = TestClient(server.create_app(labeling_model=model))

    response = _post_predict(client=client, threshold="0.5")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert model.received == []
    describe = client.get("/v1/labeling/describe")
    assert describe.status_code == status.HTTP_200_OK
    assert describe.json()["ready"] is False


def test_predict__not_an_image() -> None:
    model = FakeLabelingModel()
    client = TestClient(server.create_app(labeling_model=model))

    response = _post_predict(client=client, threshold="0.5", image=b"not an image")

    assert response.status_code == 422
    assert response.json() == {"detail": "The image cannot be decoded."}
    assert model.received == []


def test_predict__format_not_served() -> None:
    model = FakeLabelingModel()
    client = TestClient(server.create_app(labeling_model=model))
    # Pillow decodes PPM, but LightlyStudio does not import it.
    buffer = io.BytesIO()
    PILImage.new(mode="RGB", size=(WIDTH, HEIGHT)).save(buffer, format="PPM")

    response = _post_predict(client=client, threshold="0.5", image=buffer.getvalue())

    assert response.status_code == 422
    assert response.json() == {"detail": "The image cannot be decoded."}
    assert model.received == []


def test_predict__truncated_header() -> None:
    model = FakeLabelingModel()
    client = TestClient(server.create_app(labeling_model=model))
    # A header chunk of 12 bytes, one byte too short. Pillow stops before the checksum.
    truncated_png = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\x0cIHDR" + bytes(12) + bytes(4)

    response = _post_predict(client=client, threshold="0.5", image=truncated_png)

    assert response.status_code == 422
    assert response.json() == {"detail": "The image cannot be decoded."}
    assert model.received == []


def test_predict__broken_chunk() -> None:
    model = FakeLabelingModel()
    client = TestClient(server.create_app(labeling_model=model))
    png = _png_bytes()
    # A chunk is a length of 4 bytes, then a type of 4 bytes. The IDAT chunk now claims 1 byte,
    # so Pillow reads the next chunk type from the middle of the pixel data.
    type_start = png.index(b"IDAT")
    broken_png = png[: type_start - 4] + (1).to_bytes(length=4, byteorder="big") + png[type_start:]

    response = _post_predict(client=client, threshold="0.5", image=broken_png)

    assert response.status_code == 422
    assert response.json() == {"detail": "The image cannot be decoded."}
    assert model.received == []


def test_predict__too_many_pixels(monkeypatch: pytest.MonkeyPatch) -> None:
    model = FakeLabelingModel()
    client = TestClient(server.create_app(labeling_model=model))
    # Pillow refuses an image with more than twice this number of pixels. The image has 3 x 2.
    monkeypatch.setattr(PILImage, "MAX_IMAGE_PIXELS", 2)

    response = _post_predict(client=client, threshold="0.5")

    assert response.status_code == 422
    assert response.json() == {"detail": "The image cannot be decoded."}
    assert model.received == []


@pytest.mark.filterwarnings("ignore::PIL.Image.DecompressionBombWarning")
def test_predict__pixels_over_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    model = FakeLabelingModel()
    client = TestClient(server.create_app(labeling_model=model))
    # Pillow only warns about an image with 6 to 10 pixels. The image has 3 x 2.
    monkeypatch.setattr(PILImage, "MAX_IMAGE_PIXELS", 5)

    response = _post_predict(client=client, threshold="0.5")

    assert response.status_code == 422
    assert response.json() == {"detail": "The image cannot be decoded."}
    assert model.received == []


@pytest.mark.parametrize("threshold", ["1.5", "-0.1", "nan", "high"])
def test_predict__invalid_threshold(threshold: str) -> None:
    model = FakeLabelingModel()
    client = TestClient(server.create_app(labeling_model=model))

    response = _post_predict(client=client, threshold=threshold)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert model.received == []


def test_predict__model_error() -> None:
    model = FakeLabelingModel(error=RuntimeError("The model names its input."))
    client = TestClient(server.create_app(labeling_model=model), raise_server_exceptions=False)

    response = _post_predict(client=client, threshold="0.5")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {
        "detail": "The labeling model raised RuntimeError. See the server log."
    }


def test_predict__result_not_a_list(monkeypatch: pytest.MonkeyPatch) -> None:
    model = FakeLabelingModel()
    monkeypatch.setattr(model, "predict", _return_none)
    client = TestClient(server.create_app(labeling_model=model), raise_server_exceptions=False)

    response = _post_predict(client=client, threshold="0.5")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {
        "detail": "The labeling model returned NoneType, not a list of PredictedAnnotation."
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
    client = TestClient(server.create_app(labeling_model=model), raise_server_exceptions=False)

    response = _post_predict(client=client, threshold="0.5")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {
        "detail": "The labeling model returned a prediction that is not valid: "
        "The mask is not a boolean array with two dimensions."
    }


def test_predict__undeclared_class() -> None:
    model = FakeLabelingModel(
        predictions=[PredictedAnnotation(class_name="truck", box=(0.0, 0.0, 3.0, 2.0), score=0.9)],
        class_names=["car"],
    )
    client = TestClient(server.create_app(labeling_model=model), raise_server_exceptions=False)

    response = _post_predict(client=client, threshold="0.5")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {
        "detail": "The labeling model returned a prediction that is not valid: "
        "The class name 'truck' is not one of class_names."
    }


@pytest.mark.parametrize(
    "box",
    [(2.0, 0.0, 1.0, 2.0), (0.0, 1.0, 3.0, 1.0)],
    ids=["x_min over x_max", "zero height"],
)
def test_predict__box_without_positive_size(box: tuple[float, float, float, float]) -> None:
    model = FakeLabelingModel(
        predictions=[PredictedAnnotation(class_name="car", box=box, score=0.9)]
    )
    client = TestClient(server.create_app(labeling_model=model), raise_server_exceptions=False)

    response = _post_predict(client=client, threshold="0.5")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {
        "detail": "The labeling model returned a prediction that is not valid: "
        f"The box {box} does not have a positive size."
    }


def test_predict__mask_size_mismatch() -> None:
    model = FakeLabelingModel(
        predictions=[
            PredictedAnnotation(
                class_name="car",
                box=(0.0, 0.0, 1.0, 1.0),
                score=0.9,
                mask=np.ones((1, 1), dtype=np.bool_),
            )
        ]
    )
    client = TestClient(server.create_app(labeling_model=model), raise_server_exceptions=False)

    response = _post_predict(client=client, threshold="0.5")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {
        "detail": "The labeling model returned a prediction that is not valid: "
        "The mask has the size 1 x 1 pixels, but the image has the size 3 x 2 pixels."
    }


def test_predict__empty_model_id() -> None:
    model = FakeLabelingModel(model_id="")
    client = TestClient(server.create_app(labeling_model=model), raise_server_exceptions=False)

    response = _post_predict(client=client, threshold="0.5")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {
        "detail": "The labeling model has a property that is not valid: "
        "model_id: String should have at least 1 character"
    }


def _return_none(image: Image, threshold: float) -> None:
    """Stand in for ``predict`` of a model that breaks the contract."""


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
