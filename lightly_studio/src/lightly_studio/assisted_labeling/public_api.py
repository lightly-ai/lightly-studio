"""Public API for labeling models."""

from __future__ import annotations

from lightly_studio.assisted_labeling import labeling_model_registry
from lightly_studio.assisted_labeling.labeling_model import LabelingModel


def register_labeling_model(model: LabelingModel) -> None:
    """Register a model that labels images in the GUI.

    <span class="doc-badge doc-badge--beta">Beta</span>

    Call this before you start the GUI in the same process, for example with
    `ls.start_gui()`. The image editor then shows the "Label with model" tool, and the
    user can select the model there. Without a registered model, the tool is hidden.
    The registration is not saved in the dataset, so a later process must register the
    model again.

    See `examples/example_labeling_model.py` for a runnable example.

    Args:
        model: The model to register. A model with the same `model_id` is replaced.
    """
    labeling_model_registry.get_registry().register(model=model)
