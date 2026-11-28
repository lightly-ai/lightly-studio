from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from lightly_studio_serve import server
from pytest_mock import MockerFixture, MockType

from lightly_studio.assisted_labeling import (
    labeling_model_lookup,
    labeling_model_registry,
    remote_runner_cache,
)
from lightly_studio.assisted_labeling.labeling_model_registry import LabelingModelRegistry
from lightly_studio.assisted_labeling.labeling_model_runner import LocalLabelingModelRunner
from lightly_studio.assisted_labeling.provider import ProviderUnavailableError
from lightly_studio.assisted_labeling.remote_labeling_model_runner import (
    RemoteLabelingModelRunner,
)
from lightly_studio.assisted_labeling.remote_runner_cache import (
    RemoteLabelingModelConfig,
    RemoteRunnerCache,
)
from lightly_studio.embed.remote import connection
from lightly_studio.errors import NotFoundError
from tests.assisted_labeling import helpers
from tests.assisted_labeling.helpers import StubLabelingModel

DATASET_ID = UUID(int=3)
URL = "https://labeling.test"


@pytest.fixture
def registry(mocker: MockerFixture) -> LabelingModelRegistry:
    registry = LabelingModelRegistry()
    mocker.patch.object(labeling_model_registry, "_registry", registry)
    mocker.patch.object(remote_runner_cache, "_cache", RemoteRunnerCache())
    return registry


def test_get_runner_snapshot(registry: LabelingModelRegistry) -> None:
    registry.register(model=StubLabelingModel(model_id="b"))
    registry.register(model=StubLabelingModel(model_id="a"))

    snapshot = labeling_model_lookup.get_runner_snapshot()

    assert [runner.model_id for runner in snapshot.runners] == ["b", "a"]
    assert not snapshot.has_loading_models


def test_get_runner_snapshot__not_ready(registry: LabelingModelRegistry) -> None:
    loading_model = StubLabelingModel(model_id="loading")
    loading_model.is_ready = False
    registry.register(model=loading_model)
    registry.register(model=StubLabelingModel(model_id="loaded"))

    snapshot = labeling_model_lookup.get_runner_snapshot()

    assert [runner.model_id for runner in snapshot.runners] == ["loaded"]
    assert snapshot.has_loading_models


def test_get_runner_snapshot__ready_during_request(registry: LabelingModelRegistry) -> None:
    model = helpers.ReadyOnSecondReadModel(model_id="late")
    registry.register(model=model)

    snapshot = labeling_model_lookup.get_runner_snapshot()

    assert snapshot.runners == []
    assert snapshot.has_loading_models
    assert model.ready_reads == 1


def test_get_runner_snapshot__ready_raises(
    registry: LabelingModelRegistry, caplog: pytest.LogCaptureFixture
) -> None:
    registry.register(model=_ReadyRaisesModel(model_id="faulty"))
    registry.register(model=StubLabelingModel(model_id="working"))

    snapshot = labeling_model_lookup.get_runner_snapshot()

    assert [runner.model_id for runner in snapshot.runners] == ["working"]
    assert not snapshot.has_loading_models
    assert "_ReadyRaisesModel" in caplog.text


def test_get_runner_snapshot__class_names_raises(
    registry: LabelingModelRegistry, caplog: pytest.LogCaptureFixture
) -> None:
    registry.register(model=_ClassNamesRaisesModel(model_id="faulty"))
    registry.register(model=StubLabelingModel(model_id="working"))

    snapshot = labeling_model_lookup.get_runner_snapshot()

    assert [runner.model_id for runner in snapshot.runners] == ["working"]
    assert not snapshot.has_loading_models
    assert "_ClassNamesRaisesModel" in caplog.text


@pytest.mark.usefixtures("registry")
def test_get_runner_snapshot__none_registered() -> None:
    snapshot = labeling_model_lookup.get_runner_snapshot()

    assert snapshot.runners == []
    assert not snapshot.has_loading_models


def test_get_runner_snapshot__registered_then_saved(
    registry: LabelingModelRegistry, mocker: MockerFixture
) -> None:
    registry.register(model=StubLabelingModel(model_id="local"))
    _serve(mocker=mocker, model_id="remote")
    saved = [RemoteLabelingModelConfig(dataset_id=DATASET_ID, model_id="remote", url=URL)]

    snapshot = labeling_model_lookup.get_runner_snapshot(saved_models=saved)

    assert [(runner.model_id, type(runner)) for runner in snapshot.runners] == [
        ("local", LocalLabelingModelRunner),
        ("remote", RemoteLabelingModelRunner),
    ]
    assert not snapshot.has_loading_models


def test_get_runner_snapshot__registered_model_wins(
    registry: LabelingModelRegistry, mocker: MockerFixture
) -> None:
    registry.register(model=StubLabelingModel(model_id="detector"))
    build_client = _serve(mocker=mocker, model_id="detector")
    saved = [RemoteLabelingModelConfig(dataset_id=DATASET_ID, model_id="detector", url=URL)]

    snapshot = labeling_model_lookup.get_runner_snapshot(saved_models=saved)

    assert [(runner.model_id, type(runner)) for runner in snapshot.runners] == [
        ("detector", LocalLabelingModelRunner)
    ]
    assert build_client.call_count == 0


@pytest.mark.usefixtures("registry")
def test_get_runner_snapshot__skips_unavailable_server(
    mocker: MockerFixture, caplog: pytest.LogCaptureFixture
) -> None:
    # The server serves another model than the saved one, so it cannot be used.
    _serve(mocker=mocker, model_id="other")
    saved = [RemoteLabelingModelConfig(dataset_id=DATASET_ID, model_id="remote", url=URL)]

    snapshot = labeling_model_lookup.get_runner_snapshot(saved_models=saved)

    assert snapshot.runners == []
    assert not snapshot.has_loading_models
    assert "Labeling model 'remote' is not available" in caplog.text


def test_get_runner__registered_model_wins(
    registry: LabelingModelRegistry, mocker: MockerFixture
) -> None:
    registry.register(model=StubLabelingModel(model_id="detector"))
    build_client = _serve(mocker=mocker, model_id="detector")
    saved = [RemoteLabelingModelConfig(dataset_id=DATASET_ID, model_id="detector", url=URL)]

    runner = labeling_model_lookup.get_runner(model_id="detector", saved_models=saved)

    assert isinstance(runner, LocalLabelingModelRunner)
    assert build_client.call_count == 0


@pytest.mark.usefixtures("registry")
def test_get_runner__saved_server(mocker: MockerFixture) -> None:
    _serve(mocker=mocker, model_id="remote")
    saved = [RemoteLabelingModelConfig(dataset_id=DATASET_ID, model_id="remote", url=URL)]

    runner = labeling_model_lookup.get_runner(model_id="remote", saved_models=saved)

    assert runner.model_id == "remote"
    assert isinstance(runner, RemoteLabelingModelRunner)


@pytest.mark.usefixtures("registry")
def test_get_runner__unavailable_server(mocker: MockerFixture) -> None:
    _serve(mocker=mocker, model_id="other")
    saved = [RemoteLabelingModelConfig(dataset_id=DATASET_ID, model_id="remote", url=URL)]

    with pytest.raises(ProviderUnavailableError, match="serves the model 'other'"):
        labeling_model_lookup.get_runner(model_id="remote", saved_models=saved)


@pytest.mark.usefixtures("registry")
def test_get_runner__unknown_model() -> None:
    with pytest.raises(NotFoundError, match="No labeling model with ID 'm' is registered"):
        labeling_model_lookup.get_runner(model_id="m", saved_models=[])


class _ReadyRaisesModel(StubLabelingModel):
    @property
    def ready(self) -> bool:
        raise RuntimeError("The background loader failed.")


class _ClassNamesRaisesModel(StubLabelingModel):
    @property
    def class_names(self) -> list[str]:
        raise RuntimeError("The class file is missing.")


def _serve(mocker: MockerFixture, model_id: str) -> MockType:
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
