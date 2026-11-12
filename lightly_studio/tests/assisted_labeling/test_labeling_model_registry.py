from __future__ import annotations

import pytest

from lightly_studio.assisted_labeling import labeling_model_registry
from lightly_studio.assisted_labeling.labeling_model_registry import LabelingModelRegistry
from tests.assisted_labeling.helpers import StubLabelingModel


class TestLabelingModelRegistry:
    def test_register(self) -> None:
        registry = LabelingModelRegistry()
        first = StubLabelingModel(model_id="b")
        second = StubLabelingModel(model_id="a")

        registry.register(model=first)
        registry.register(model=second)

        assert registry.list_models() == [first, second]

    def test_register__replaces_same_id(self, caplog: pytest.LogCaptureFixture) -> None:
        registry = LabelingModelRegistry()
        old = StubLabelingModel(model_id="m")
        new = StubLabelingModel(model_id="m")

        registry.register(model=old)
        registry.register(model=new)

        assert registry.list_models() == [new]
        assert "Replacing labeling model 'm'." in caplog.text

    def test_get(self) -> None:
        registry = LabelingModelRegistry()
        model = StubLabelingModel(model_id="m")
        registry.register(model=model)

        assert registry.get(model_id="m") is model
        assert registry.get(model_id="other") is None


def test_get_registry() -> None:
    assert labeling_model_registry.get_registry() is labeling_model_registry.get_registry()
