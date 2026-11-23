"""Finds the labeling models that the GUI can run."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

from lightly_studio_serve.labeling import LabelingModel

from lightly_studio.assisted_labeling import labeling_model_registry
from lightly_studio.assisted_labeling.labeling_model_runner import (
    LabelingModelRunner,
    LocalLabelingModelRunner,
)
from lightly_studio.errors import NotFoundError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RunnerSnapshot:
    """The labeling models that can run now, and if more models are still loading.

    Both fields come from one read of `ready` for each model. A model that becomes ready
    during the request is then either in `runners` or counted in `has_loading_models`.

    Attributes:
        runners: A runner for each model that is ready, in registration order.
        has_loading_models: True if a registered model is not ready yet.
    """

    runners: list[LabelingModelRunner]
    has_loading_models: bool


class _NotRunnable(Enum):
    LOADING = "loading"
    FAILED = "failed"


def get_runner_snapshot() -> RunnerSnapshot:
    """Return the runners of the ready labeling models, and if a model is still loading.

    A model with a property that raises an error is left out and logged, so that the other
    models stay available. Such a model is not loading.
    """
    models = labeling_model_registry.get_registry().list_models()
    results = [_create_runner_if_ready(model=model) for model in models]
    return RunnerSnapshot(
        runners=[result for result in results if not isinstance(result, _NotRunnable)],
        has_loading_models=_NotRunnable.LOADING in results,
    )


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


def _create_runner_if_ready(model: LabelingModel) -> LabelingModelRunner | _NotRunnable:
    """Return a runner for the model, or the reason that the model cannot run now.

    The properties of a model are user code and can raise any error.
    """
    try:
        if not model.ready:
            return _NotRunnable.LOADING
        return LocalLabelingModelRunner(model=model)
    except Exception:
        # The class name, because `model_id` is user code and can raise too
        logger.exception("Leaving out the labeling model of type %s.", type(model).__name__)
        return _NotRunnable.FAILED
