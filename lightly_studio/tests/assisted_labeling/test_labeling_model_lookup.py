from __future__ import annotations

import pytest
from pytest_mock import MockerFixture

from lightly_studio.assisted_labeling import labeling_model_lookup, labeling_model_registry
from lightly_studio.assisted_labeling.labeling_model_registry import LabelingModelRegistry
from tests.assisted_labeling import helpers
from tests.assisted_labeling.helpers import StubLabelingModel


class _ReadyRaisesModel(StubLabelingModel):
    @property
    def ready(self) -> bool:
        raise RuntimeError("The background loader failed.")


class _ClassNamesRaisesModel(StubLabelingModel):
    @property
    def class_names(self) -> list[str]:
        raise RuntimeError("The class file is missing.")


@pytest.fixture
def model_registry(mocker: MockerFixture) -> LabelingModelRegistry:
    registry = LabelingModelRegistry()
    mocker.patch.object(labeling_model_registry, "_registry", registry)
    return registry


def test_get_runner_snapshot(model_registry: LabelingModelRegistry) -> None:
    model_registry.register(model=StubLabelingModel(model_id="b"))
    model_registry.register(model=StubLabelingModel(model_id="a"))

    snapshot = labeling_model_lookup.get_runner_snapshot()

    assert [runner.model_id for runner in snapshot.runners] == ["b", "a"]
    assert not snapshot.has_loading_models


def test_get_runner_snapshot__not_ready(model_registry: LabelingModelRegistry) -> None:
    loading_model = StubLabelingModel(model_id="loading")
    loading_model.is_ready = False
    model_registry.register(model=loading_model)
    model_registry.register(model=StubLabelingModel(model_id="loaded"))

    snapshot = labeling_model_lookup.get_runner_snapshot()

    assert [runner.model_id for runner in snapshot.runners] == ["loaded"]
    assert snapshot.has_loading_models


def test_get_runner_snapshot__ready_during_request(
    model_registry: LabelingModelRegistry,
) -> None:
    model = helpers.ReadyOnSecondReadModel(model_id="late")
    model_registry.register(model=model)

    snapshot = labeling_model_lookup.get_runner_snapshot()

    assert snapshot.runners == []
    assert snapshot.has_loading_models
    assert model.ready_reads == 1


def test_get_runner_snapshot__ready_raises(
    model_registry: LabelingModelRegistry, caplog: pytest.LogCaptureFixture
) -> None:
    model_registry.register(model=_ReadyRaisesModel(model_id="faulty"))
    model_registry.register(model=StubLabelingModel(model_id="working"))

    snapshot = labeling_model_lookup.get_runner_snapshot()

    assert [runner.model_id for runner in snapshot.runners] == ["working"]
    assert not snapshot.has_loading_models
    assert "_ReadyRaisesModel" in caplog.text


def test_get_runner_snapshot__class_names_raises(
    model_registry: LabelingModelRegistry, caplog: pytest.LogCaptureFixture
) -> None:
    model_registry.register(model=_ClassNamesRaisesModel(model_id="faulty"))
    model_registry.register(model=StubLabelingModel(model_id="working"))

    snapshot = labeling_model_lookup.get_runner_snapshot()

    assert [runner.model_id for runner in snapshot.runners] == ["working"]
    assert not snapshot.has_loading_models
    assert "_ClassNamesRaisesModel" in caplog.text


@pytest.mark.usefixtures("model_registry")
def test_get_runner_snapshot__none_registered() -> None:
    snapshot = labeling_model_lookup.get_runner_snapshot()

    assert snapshot.runners == []
    assert not snapshot.has_loading_models
