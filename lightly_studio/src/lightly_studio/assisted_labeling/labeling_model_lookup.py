"""Finds the labeling models that the GUI can run."""

from __future__ import annotations

from lightly_studio.assisted_labeling import labeling_model_registry
from lightly_studio.assisted_labeling.labeling_model_runner import (
    LabelingModelRunner,
    LocalLabelingModelRunner,
)
from lightly_studio.assisted_labeling.provider import ProviderUnavailableError
from lightly_studio.errors import NotFoundError


def list_runners() -> list[LabelingModelRunner]:
    """Return a runner for each labeling model that can run now, in registration order.

    A model that is still loading is left out.
    """
    models = labeling_model_registry.get_registry().list_models()
    return [LocalLabelingModelRunner(model=model) for model in models if model.ready]


def get_runner(model_id: str) -> LabelingModelRunner:
    """Return the runner of the labeling model with the ID.

    Raises:
        NotFoundError: If no labeling model has the ID.
        ProviderUnavailableError: If the labeling model is still loading.
    """
    model = labeling_model_registry.get_registry().get(model_id=model_id)
    if model is None:
        raise NotFoundError(f"No labeling model with ID {model_id!r} is registered.")
    if not model.ready:
        raise ProviderUnavailableError(
            f"The labeling model {model_id!r} is still loading. Try again later."
        )
    return LocalLabelingModelRunner(model=model)
