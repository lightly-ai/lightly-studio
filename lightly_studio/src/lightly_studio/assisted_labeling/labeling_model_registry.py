"""Registry of the models that label images in the GUI."""

from __future__ import annotations

import logging
import threading

from lightly_studio_serve.labeling import LabelingModel

logger = logging.getLogger(__name__)


class LabelingModelRegistry:
    """Stores the labeling models of this process by model ID, in registration order."""

    def __init__(self) -> None:
        """Create an empty registry."""
        self._model_id_to_model: dict[str, LabelingModel] = {}
        self._lock = threading.Lock()

    def register(self, model: LabelingModel) -> None:
        """Register a model. A model with the same ID is replaced."""
        model_id = model.model_id
        with self._lock:
            if model_id in self._model_id_to_model:
                logger.warning("Replacing labeling model %r.", model_id)
            self._model_id_to_model[model_id] = model

    def get(self, model_id: str) -> LabelingModel | None:
        """Return the model with the ID, or None if no model has it."""
        with self._lock:
            return self._model_id_to_model.get(model_id)

    def list_models(self) -> list[LabelingModel]:
        """Return all models in registration order."""
        with self._lock:
            return list(self._model_id_to_model.values())


_registry = LabelingModelRegistry()


def get_registry() -> LabelingModelRegistry:
    """Return the process-wide labeling model registry."""
    return _registry
