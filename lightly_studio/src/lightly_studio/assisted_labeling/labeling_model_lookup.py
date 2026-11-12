"""Finds the labeling models that the GUI can run.

A model that is registered in this process wins over a server that the dataset saves
under the same model ID. This is the same order as for embedders.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from lightly_studio.assisted_labeling import labeling_model_registry, remote_runner_cache
from lightly_studio.assisted_labeling.labeling_model_runner import (
    LabelingModelRunner,
    LocalLabelingModelRunner,
)
from lightly_studio.assisted_labeling.provider import ProviderUnavailableError
from lightly_studio.assisted_labeling.remote_labeling_model_runner import RemoteLabelingModelError
from lightly_studio.assisted_labeling.remote_runner_cache import RemoteLabelingModelConfig
from lightly_studio.errors import NotFoundError

logger = logging.getLogger(__name__)


def list_runners(saved_models: Sequence[RemoteLabelingModelConfig]) -> list[LabelingModelRunner]:
    """Return a runner for each labeling model that can run now.

    The registered models come first, in registration order. The saved servers follow.
    A saved server that cannot be connected is left out, with a warning in the log.

    Args:
        saved_models: The labeling servers that the dataset saves.
    """
    registry = labeling_model_registry.get_registry()
    runners: list[LabelingModelRunner] = [
        LocalLabelingModelRunner(model=model) for model in registry.list_models()
    ]
    registered_ids = {runner.model_id for runner in runners}
    for config in saved_models:
        if config.model_id in registered_ids:
            continue
        try:
            runners.append(remote_runner_cache.get_cache().get(config=config))
        except RemoteLabelingModelError as error:
            logger.warning("Labeling model %r is not available: %s", config.model_id, error)
    return runners


def get_runner(
    model_id: str, saved_models: Sequence[RemoteLabelingModelConfig]
) -> LabelingModelRunner:
    """Return the runner of the labeling model with the ID.

    Args:
        model_id: The ID of the labeling model.
        saved_models: The labeling servers that the dataset saves.

    Raises:
        NotFoundError: If no labeling model has the ID.
        ProviderUnavailableError: If the server of the model cannot be connected.
    """
    model = labeling_model_registry.get_registry().get(model_id=model_id)
    if model is not None:
        return LocalLabelingModelRunner(model=model)
    for config in saved_models:
        if config.model_id != model_id:
            continue
        try:
            return remote_runner_cache.get_cache().get(config=config)
        except RemoteLabelingModelError as error:
            raise ProviderUnavailableError(str(error)) from error
    raise NotFoundError(f"No labeling model with ID {model_id!r} is registered.")
