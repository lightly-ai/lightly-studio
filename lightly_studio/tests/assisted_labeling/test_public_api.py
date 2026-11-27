from __future__ import annotations

from pytest_mock import MockerFixture

import lightly_studio as ls
from lightly_studio.assisted_labeling import labeling_model_registry
from lightly_studio.assisted_labeling.labeling_model_registry import LabelingModelRegistry
from tests.assisted_labeling.helpers import StubLabelingModel


def test_register_labeling_model(mocker: MockerFixture) -> None:
    registry = LabelingModelRegistry()
    mocker.patch.object(labeling_model_registry, "_registry", registry)
    model = StubLabelingModel(model_id="m")

    ls.register_labeling_model(model=model)

    assert registry.list_models() == [model]
