from __future__ import annotations

import pytest
from pytest_mock import MockerFixture

from lightly_studio.assisted_labeling import labeling_model_lookup, labeling_model_registry
from lightly_studio.assisted_labeling.labeling_model_registry import LabelingModelRegistry
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


def test_list_runners(model_registry: LabelingModelRegistry) -> None:
    model_registry.register(model=StubLabelingModel(model_id="b"))
    model_registry.register(model=StubLabelingModel(model_id="a"))

    runners = labeling_model_lookup.list_runners()

    assert [runner.model_id for runner in runners] == ["b", "a"]


def test_list_runners__not_ready(model_registry: LabelingModelRegistry) -> None:
    loading_model = StubLabelingModel(model_id="loading")
    loading_model.is_ready = False
    model_registry.register(model=loading_model)
    model_registry.register(model=StubLabelingModel(model_id="loaded"))

    runners = labeling_model_lookup.list_runners()

    assert [runner.model_id for runner in runners] == ["loaded"]


def test_list_runners__ready_raises(
    model_registry: LabelingModelRegistry, caplog: pytest.LogCaptureFixture
) -> None:
    model_registry.register(model=_ReadyRaisesModel(model_id="faulty"))
    model_registry.register(model=StubLabelingModel(model_id="working"))

    runners = labeling_model_lookup.list_runners()

    assert [runner.model_id for runner in runners] == ["working"]
    assert "_ReadyRaisesModel" in caplog.text


def test_list_runners__class_names_raises(
    model_registry: LabelingModelRegistry, caplog: pytest.LogCaptureFixture
) -> None:
    model_registry.register(model=_ClassNamesRaisesModel(model_id="faulty"))
    model_registry.register(model=StubLabelingModel(model_id="working"))

    runners = labeling_model_lookup.list_runners()

    assert [runner.model_id for runner in runners] == ["working"]
    assert "_ClassNamesRaisesModel" in caplog.text
