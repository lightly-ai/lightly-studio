"""Example of labeling images in the GUI with your own model.

The script wraps a LightlyTrain model in a ``LabelingModel``, registers it and starts the
GUI. Open an image, turn on edit mode and select "Label with model" in the toolbar. The
model suggests annotations, and you keep the correct ones.

Any model works: subclass ``ls.LabelingModel`` and return ``ls.PredictedAnnotation`` objects
from ``predict``.

Install LightlyTrain to run the example:

    pip install lightly-train lightly-studio
"""

from __future__ import annotations

import io
import threading
from typing import Any

import lightly_train  # type: ignore[import-not-found]
from environs import Env
from PIL import Image

import lightly_studio as ls
from lightly_studio.assisted_labeling.provider import ProviderImage
from lightly_studio.database import db_manager

# A LightlyTrain model name or the path of a checkpoint that you trained.
MODEL = "ltdetrv2-s-coco"


class LightlyTrainLabelingModel(ls.LabelingModel):
    """Runs a LightlyTrain model in this process."""

    def __init__(self, model: str, task: ls.ModelTask = ls.ModelTask.OBJECT_DETECTION) -> None:
        """Loads the model.

        Args:
            model: A LightlyTrain model name or checkpoint path.
            task: Task of the model. Instance segmentation models return masks.
        """
        self._model_id = model
        self._task = task
        self._model: Any = lightly_train.load_model(model=model)
        self._classes: dict[int, str] = dict(self._model.classes)
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
        return [name for _, name in sorted(self._classes.items())]

    def predict(self, image: ProviderImage, threshold: float) -> list[ls.PredictedAnnotation]:
        """Predicts the annotations of the image."""
        pil_image = Image.open(io.BytesIO(image.read_bytes())).convert("RGB")
        with self._lock:
            output = self._model.predict(image=pil_image, threshold=threshold)
        labels = output["labels"].cpu().tolist()
        scores = output["scores"].detach().cpu().float().tolist()
        boxes = output["bboxes"].detach().cpu().float().reshape(-1, 4).tolist()
        masks = (
            (output["masks"].detach().cpu() > 0).numpy()
            if self._task == ls.ModelTask.INSTANCE_SEGMENTATION
            else None
        )
        return [
            ls.PredictedAnnotation(
                class_name=self._classes[int(label)],
                box=(box[0], box[1], box[2], box[3]),
                score=score,
                mask=None if masks is None else masks[index],
            )
            for index, (label, score, box) in enumerate(zip(labels, scores, boxes))
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


if __name__ == "__main__":
    main()
