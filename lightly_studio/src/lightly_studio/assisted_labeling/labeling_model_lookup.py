"""Finds the labeling models that the GUI can run."""

from __future__ import annotations

import logging

from lightly_studio_serve.labeling import LabelingModel

from lightly_studio.assisted_labeling import labeling_model_registry
from lightly_studio.assisted_labeling.labeling_model_runner import (
    LabelingModelRunner,
    LocalLabelingModelRunner,
)
from lightly_studio.errors import NotFoundError

logger = logging.getLogger(__name__)


def list_runners() -> list[LabelingModelRunner]:
    """Return a runner for each labeling model that can run now, in registration order.

    A model that is still loading is left out. A model with a property that raises an
    error is left out and logged, so that the other models stay available.
    """
    models = labeling_model_registry.get_registry().list_models()
    runners = [_create_runner_if_ready(model=model) for model in models]
    return [runner for runner in runners if runner is not None]


def get_runner(model_id: str) -> LabelingModelRunner:
    """Return the runner of the labeling model with the ID.

    The runner, not this function, checks that the model is ready.

    Raises:
        NotFoundError: If no labeling model has the ID.
    """
    model = labeling_model_registry.get_registry().get(model_id=model_id)
    if model is None:
        raise NotFoundError(f"No labeling model with ID {model_id!r} is registered.")
    return LocalLabelingModelRunner(model=model)


def _create_runner_if_ready(model: LabelingModel) -> LabelingModelRunner | None:
    """Return a runner for the model, or None if the model is loading or fails.

    The properties of a model are user code and can raise any error.
    """
    try:
        if not model.ready:
            return None
        return LocalLabelingModelRunner(model=model)
    except Exception:
        # The class name, because `model_id` is user code and can raise too
        logger.exception("Leaving out the labeling model of type %s.", type(model).__name__)
        return None
