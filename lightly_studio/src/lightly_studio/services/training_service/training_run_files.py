"""The files that Studio and the training process share for one training run."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TrainingRunFiles:
    """The paths of the files in the folder of one training run."""

    run_dir: Path

    @property
    def config_file(self) -> Path:
        """The config that the training process reads."""
        return self.run_dir / "config.json"

    @property
    def train_annotations_file(self) -> Path:
        """The COCO annotations of the train samples."""
        return self.run_dir / "train.json"

    @property
    def val_annotations_file(self) -> Path:
        """The COCO annotations of the val samples."""
        return self.run_dir / "val.json"

    @property
    def predict_images_file(self) -> Path:
        """The images to predict on, as a list of `{"sample_id": ..., "path": ...}`."""
        return self.run_dir / "predict_images.json"

    @property
    def predictions_file(self) -> Path:
        """The predictions that the training process writes."""
        return self.run_dir / "predictions.json"

    @property
    def stage_file(self) -> Path:
        """The current stage of the training process: "training" or "predicting"."""
        return self.run_dir / "stage.txt"

    @property
    def out_dir(self) -> Path:
        """The LightlyTrain output folder."""
        return self.run_dir / "lightly_train"

    @property
    def train_log_file(self) -> Path:
        """The LightlyTrain log with the training progress."""
        return self.out_dir / "train.log"

    @property
    def process_log_file(self) -> Path:
        """The stdout and stderr of the training process."""
        return self.run_dir / "process.log"
