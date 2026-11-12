"""Public API for labeling models."""

from __future__ import annotations

from typing import Any

from lightly_studio_serve.labeling_model import LabelingModel

from lightly_studio.assisted_labeling import labeling_model_registry, remote_runner_cache
from lightly_studio.core.dataset import Dataset
from lightly_studio.models.labeling_model import LabelingModelCreate
from lightly_studio.resolvers import labeling_model_resolver


def register_labeling_model(model: LabelingModel) -> None:
    """Register a model that labels images in the GUI.

    <span class="doc-badge doc-badge--beta">Beta</span>

    Call this before you start the GUI in the same process, for example with
    ``ls.start_gui()``. The registration is not saved in the dataset, so a later process
    must register the model again.

    Args:
        model: The model to register. A model with the same ``model_id`` is replaced.
    """
    labeling_model_registry.get_registry().register(model=model)


def register_remote_labeling_model(
    dataset: Dataset[Any], url: str, api_key: str | None = None
) -> None:
    """Label the images of a dataset with a model on a remote server.

    <span class="doc-badge doc-badge--beta">Beta</span>

    The dataset stores ``url`` and ``api_key`` in plain text. A later process, such as
    ``lightly-studio gui``, then shows the model in the GUI with no registration. A model
    that ``register_labeling_model`` registered in the process of the GUI with the same
    ``model_id`` is used instead of the server.

    Call the function again to change the URL or the key of a model.

    Args:
        dataset: The dataset whose images the model labels.
        url: The base URL of a server that ``lightly_studio_serve.serve`` runs with a
            ``labeling_model``, or of another server that speaks the same protocol.
        api_key: The bearer token of the server, or None if the server needs none.

    Raises:
        RemoteLabelingModelError: If the server cannot be reached or used. Nothing is
            stored then.
    """
    runner = remote_runner_cache.connect(url=url, api_key=api_key)
    model_id = runner.model_id
    runner.close()
    labeling_model_resolver.set_remote(
        session=dataset.session,
        labeling_model=LabelingModelCreate(
            dataset_id=dataset.dataset_id, model_id=model_id, url=url, api_key=api_key
        ),
    )
