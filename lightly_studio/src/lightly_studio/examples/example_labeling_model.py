"""Example of labeling images in the GUI with your own model.

The script wraps a LightlyTrain model in a ``LabelingModel``, registers it and starts the
GUI. Open an image, turn on edit mode and select "Auto-label" in the toolbar. The
model suggests annotations, and you keep the correct ones.

Any model works: subclass ``ls.LabelingModel`` and return ``ls.PredictedAnnotation`` objects
from ``predict``.

Install LightlyTrain to run the example:

    pip install lightly-train lightly-studio
"""

from __future__ import annotations

import threading
from typing import Any

import lightly_train  # type: ignore[import-not-found]
import numpy as np
from environs import Env
from numpy.typing import NDArray
from PIL.Image import Image

import lightly_studio as ls
from lightly_studio.database import db_manager

# A LightlyTrain model name or the path of a checkpoint that you trained.
MODEL = "ltdetrv2-s-coco"


class LightlyTrainLabelingModel(ls.LabelingModel):
    """Runs a LightlyTrain model in this process."""

    def __init__(self, model: str, task: ls.ModelTask = ls.ModelTask.OBJECT_DETECTION) -> None:
        """Load the model.

        Args:
            model: A LightlyTrain model name or checkpoint path.
            task: The task of the model. An instance segmentation model returns masks.
                If the model returns no boxes, as EoMT models do, each box comes from
                its mask.
        """
        self._model_id = model
        self._task = task
        self._model: Any = lightly_train.load_model(model=model)
        self._class_id_to_name: dict[int, str] = dict(self._model.classes)
        # The GUI server calls predict from several threads, and the model is not thread-safe
        self._lock = threading.Lock()

    @property
    def model_id(self) -> str:
        """The model name, shown in the GUI."""
        return self._model_id

    @property
    def task(self) -> ls.ModelTask:
        """The task of the model."""
        return self._task

    @property
    def class_names(self) -> list[str]:
        """The class names, ordered by class ID."""
        return [name for _, name in sorted(self._class_id_to_name.items())]

    def predict(self, image: Image, threshold: float) -> list[ls.PredictedAnnotation]:
        """Predict the annotations of the image."""
        with self._lock:
            output = self._model.predict(image=image, threshold=threshold)
        labels = output["labels"].cpu().tolist()
        scores = output["scores"].detach().cpu().float().tolist()
        masks = (
            (output["masks"].detach().cpu() > 0).numpy()
            if self._task == ls.ModelTask.INSTANCE_SEGMENTATION
            else None
        )
        boxes = _get_boxes(output=output, masks=masks)
        return [
            ls.PredictedAnnotation(
                class_name=self._class_id_to_name[int(label)],
                box=box,
                score=score,
                mask=None if masks is None else masks[index],
            )
            for index, (label, score, box) in enumerate(zip(labels, scores, boxes))
            # A box cannot come from an empty mask
            if box is not None
        ]


def main() -> None:
    """Register the model, create the dataset and start the GUI."""
    env = Env()
    env.read_env()

    db_manager.connect(cleanup_existing=True)
    ls.register_labeling_model(model=LightlyTrainLabelingModel(model=MODEL))
    dataset = ls.ImageDataset.create()
    dataset.add_images_from_path(path=env.path("EXAMPLES_DATASET_PATH"))
    ls.start_gui()


def _get_boxes(
    output: dict[str, Any], masks: NDArray[np.bool_] | None
) -> list[tuple[float, float, float, float] | None]:
    """Get the box of each prediction from the model output, or from the masks.

    Args:
        output: The output of the LightlyTrain model.
        masks: The predicted masks, or None for a model without masks.

    Returns:
        One box for each prediction, or None for a prediction with an empty mask.

    Raises:
        ValueError: If the output has no boxes and no masks.
    """
    if "bboxes" in output:
        boxes = output["bboxes"].detach().cpu().float().reshape(-1, 4).tolist()
        return [(box[0], box[1], box[2], box[3]) for box in boxes]
    if masks is None:
        raise ValueError(
            "The model returns no boxes. Use task=ModelTask.INSTANCE_SEGMENTATION to get "
            "each box from its mask."
        )
    return [_box_from_mask(mask=mask) for mask in masks]


def _box_from_mask(mask: NDArray[np.bool_]) -> tuple[float, float, float, float] | None:
    """Get the smallest box that contains the mask, or None for an empty mask.

    The max values are exclusive, so the box contains the last pixel of the mask.
    """
    rows = np.flatnonzero(mask.any(axis=1))
    columns = np.flatnonzero(mask.any(axis=0))
    if rows.size == 0:
        return None
    return (float(columns[0]), float(rows[0]), float(columns[-1] + 1), float(rows[-1] + 1))


if __name__ == "__main__":
    main()
