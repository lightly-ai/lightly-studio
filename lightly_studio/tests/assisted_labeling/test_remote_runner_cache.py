from __future__ import annotations

import time
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from lightly_studio_serve import server
from pytest_mock import MockerFixture

from lightly_studio.assisted_labeling import remote_runner_cache
from lightly_studio.assisted_labeling.remote_labeling_model_runner import RemoteLabelingModelError
from lightly_studio.assisted_labeling.remote_runner_cache import (
    RemoteLabelingModelConfig,
    RemoteRunnerCache,
)
from lightly_studio.embed.remote import connection
from tests.assisted_labeling.helpers import StubLabelingModel

DATASET_ID = UUID(int=3)
URL = "https://labeling.test"


class TestRemoteRunnerCache:
    def test_get__builds_once(self, mocker: MockerFixture) -> None:
        build_client = _serve(mocker=mocker, model_id="m")
        cache = RemoteRunnerCache()
        config = RemoteLabelingModelConfig(dataset_id=DATASET_ID, model_id="m", url=URL)

        first = cache.get(config=config)
        second = cache.get(config=config)

        assert first is second
        assert first.model_id == "m"
        assert build_client.call_count == 1

    def test_get__changed_config_builds_again(self, mocker: MockerFixture) -> None:
        build_client = _serve(mocker=mocker, model_id="m")
        cache = RemoteRunnerCache()

        first = cache.get(
            config=RemoteLabelingModelConfig(dataset_id=DATASET_ID, model_id="m", url=URL)
        )
        second = cache.get(
            config=RemoteLabelingModelConfig(
                dataset_id=DATASET_ID, model_id="m", url="https://other.test"
            )
        )

        assert first is not second
        assert build_client.call_count == 2

    def test_get__failure_is_remembered_then_retried(self, mocker: MockerFixture) -> None:
        build_client = _serve(mocker=mocker, model_id="other")
        monotonic = mocker.patch.object(time, "monotonic", return_value=100.0)
        cache = RemoteRunnerCache()
        config = RemoteLabelingModelConfig(dataset_id=DATASET_ID, model_id="m", url=URL)

        with pytest.raises(RemoteLabelingModelError, match="serves the model 'other'"):
            cache.get(config=config)
        # 29 seconds later the failure is still remembered, so no server is called.
        monotonic.return_value = 129.0
        with pytest.raises(RemoteLabelingModelError, match="serves the model 'other'"):
            cache.get(config=config)
        assert build_client.call_count == 1

        # 30 seconds after the failure the server is tried again. It now serves "m".
        _serve(mocker=mocker, model_id="m")
        monotonic.return_value = 130.0
        assert cache.get(config=config).model_id == "m"


def test_connect__url_does_not_parse() -> None:
    with pytest.raises(RemoteLabelingModelError, match="is refused"):
        remote_runner_cache.connect(url="not a url", api_key=None)


def _serve(mocker: MockerFixture, model_id: str) -> MagicMock:
    """Serve a labeling model with the ID to every client that opens."""
    return mocker.patch.object(
        connection,
        "build_client",
        side_effect=lambda url: TestClient(
            server.create_app(labeling_model=StubLabelingModel(model_id=model_id)),
            base_url=url,
            follow_redirects=False,
        ),
    )
