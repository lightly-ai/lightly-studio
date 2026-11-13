"""Public API for labeling models."""

from __future__ import annotations

from lightly_studio_serve.labeling import LabelingModel

from lightly_studio.assisted_labeling import labeling_model_registry


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
