from __future__ import annotations

import httpx
import numpy as np
import pytest
from fastapi.testclient import TestClient
from lightly_studio_serve import server
from lightly_studio_serve.labeling_model import LabelingModel, ModelTask
from lightly_studio_serve.types import PredictedAnnotation

from lightly_studio.assisted_labeling.provider import (
    ProviderError,
    ProviderImage,
    ProviderUnavailableError,
)
from lightly_studio.assisted_labeling.remote_labeling_model_runner import (
    RemoteLabelingModelError,
    RemoteLabelingModelRunner,
)
from tests.assisted_labeling import helpers
from tests.assisted_labeling.helpers import StubLabelingModel

URL = "https://labeling.test"
WIDTH = 3
HEIGHT = 2


class _LoadingModel(StubLabelingModel):
    @property
    def ready(self) -> bool:
        return False


class TestRemoteLabelingModelRunner:
    def test_connect(self) -> None:
        model = StubLabelingModel(
            model_id="seg", task=ModelTask.INSTANCE_SEGMENTATION, class_names=["car", "person"]
        )

        runner = RemoteLabelingModelRunner.connect(client=_client(model=model))

        assert runner.model_id == "seg"
        assert runner.task is ModelTask.INSTANCE_SEGMENTATION
        assert runner.class_names == ["car", "person"]

    def test_connect__wrong_api_key(self) -> None:
        client = _client(model=StubLabelingModel(model_id="m"), api_key="secret")

        with pytest.raises(RemoteLabelingModelError, match="rejects the API key"):
            RemoteLabelingModelRunner.connect(client=client, api_key="wrong")

    def test_connect__not_a_labeling_server(self) -> None:
        client = httpx.Client(
            base_url=URL,
            transport=httpx.MockTransport(lambda _request: httpx.Response(404, text="Not Found")),
        )

        with pytest.raises(RemoteLabelingModelError, match="answered 404: Not Found"):
            RemoteLabelingModelRunner.connect(client=client)

    def test_connect__no_answer(self) -> None:
        def refuse(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("refused", request=request)

        client = httpx.Client(base_url=URL, transport=httpx.MockTransport(refuse))

        with pytest.raises(RemoteLabelingModelError, match="gives no answer: ConnectError"):
            RemoteLabelingModelRunner.connect(client=client)

    def test_connect__client_follows_redirects(self) -> None:
        client = TestClient(
            server.create_app(labeling_model=StubLabelingModel(model_id="m")),
            base_url=URL,
            follow_redirects=True,
        )

        with pytest.raises(RemoteLabelingModelError, match="is refused"):
            RemoteLabelingModelRunner.connect(client=client)

    def test_connect__other_major_version(self) -> None:
        body = {
            "protocol_version": "2.0",
            "model_id": "m",
            "task": "object_detection",
            "class_names": [],
            "ready": True,
            "limits": {},
        }
        client = httpx.Client(
            base_url=URL,
            transport=httpx.MockTransport(lambda _request: httpx.Response(200, json=body)),
        )

        with pytest.raises(RemoteLabelingModelError, match=r"speaks protocol '2\.0'"):
            RemoteLabelingModelRunner.connect(client=client)

    def test_predict(self) -> None:
        mask = np.array([[True, False, False], [False, True, True]], dtype=np.bool_)
        model = StubLabelingModel(
            model_id="seg",
            task=ModelTask.INSTANCE_SEGMENTATION,
            class_names=["car"],
            predictions=[
                PredictedAnnotation(
                    class_name="car", box=(0.0, 0.0, 3.0, 2.0), score=0.9, mask=mask
                ),
                PredictedAnnotation(class_name="car", box=(1.0, 0.0, 2.0, 1.0), score=0.6),
            ],
        )
        runner = RemoteLabelingModelRunner.connect(
            client=_client(model=model, api_key="secret"), api_key="secret"
        )

        first, second = runner.predict(image=_image(), threshold=0.25)

        assert model.thresholds == [0.25]
        assert [pil_image.size for pil_image in model.images] == [(WIDTH, HEIGHT)]
        assert (first.class_name, first.box, first.score) == ("car", (0.0, 0.0, 3.0, 2.0), 0.9)
        assert first.mask is not None
        np.testing.assert_array_equal(first.mask, mask)
        assert second == PredictedAnnotation(class_name="car", box=(1.0, 0.0, 2.0, 1.0), score=0.6)

    def test_predict__model_error(self) -> None:
        model = StubLabelingModel(model_id="m", error=RuntimeError("secret output"))
        runner = RemoteLabelingModelRunner.connect(client=_client(model=model))

        with pytest.raises(ProviderError) as error_info:
            runner.predict(image=_image(), threshold=0.5)

        assert str(error_info.value) == (
            "The labeling server answered 500: "
            "The labeling model raised RuntimeError. See the server log."
        )

    def test_predict__model_not_ready(self) -> None:
        runner = RemoteLabelingModelRunner.connect(
            client=_client(model=_LoadingModel(model_id="m"))
        )

        with pytest.raises(ProviderUnavailableError, match="is not ready: The model is still"):
            runner.predict(image=_image(), threshold=0.5)

    def test_predict__server_changed_model(self) -> None:
        runner = RemoteLabelingModelRunner.connect(
            client=_client(model=StubLabelingModel(model_id="old"))
        )
        runner._client = _client(model=StubLabelingModel(model_id="new"))

        with pytest.raises(ProviderError, match="answered for the model 'new', expected 'old'"):
            runner.predict(image=_image(), threshold=0.5)


def _client(model: LabelingModel, api_key: str | None = None) -> httpx.Client:
    """Return a client that drives a labeling server in this process."""
    return TestClient(
        server.create_app(labeling_model=model, api_key=api_key),
        base_url=URL,
        follow_redirects=False,
        raise_server_exceptions=False,
    )


def _image() -> ProviderImage:
    return helpers.make_image(
        width=WIDTH, height=HEIGHT, data=helpers.png_bytes(width=WIDTH, height=HEIGHT)
    )
