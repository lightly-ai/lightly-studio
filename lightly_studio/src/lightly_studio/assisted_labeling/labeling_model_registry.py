"""Registry of the models that label images in the GUI."""

from __future__ import annotations

import logging
import threading

from lightly_studio.assisted_labeling.labeling_model import LabelingModel

logger = logging.getLogger(__name__)


class LabelingModelRegistry:
    """Stores the labeling models by model ID, in registration order."""

    def __init__(self) -> None:
        """Creates an empty registry."""
        self._models: dict[str, LabelingModel] = {}
        self._lock = threading.Lock()

    def register(self, model: LabelingModel) -> None:
        """Registers a model. Replaces a model with the same ID."""
        model_id = model.model_id
        with self._lock:
            if model_id in self._models:
                logger.warning("Replacing labeling model %r.", model_id)
            self._models[model_id] = model

    def get(self, model_id: str) -> LabelingModel | None:
        """Returns the model with the ID, or None if no model has it."""
        with self._lock:
            return self._models.get(model_id)

    def list_models(self) -> list[LabelingModel]:
        """Returns all models in registration order."""
        with self._lock:
            return list(self._models.values())

    def clear(self) -> None:
        """Removes all models."""
        with self._lock:
            self._models.clear()


_registry = LabelingModelRegistry()


def get_registry() -> LabelingModelRegistry:
    """Returns the process-wide labeling model registry."""
    return _registry
