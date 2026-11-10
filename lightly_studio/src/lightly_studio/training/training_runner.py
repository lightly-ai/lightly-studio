"""Train an object detection model with LightlyTrain and predict on images.

LightlyStudio starts this script as a child process. Studio does not import this module,
so Studio works without LightlyTrain. The script does not import lightly_studio and does
not access the database. It reads a JSON config file and writes
its results to the files that the config names:

- `stage_file`: The current stage, "training" or "predicting".
- `out_dir`: The LightlyTrain output, which includes `train.log` and the checkpoints.
- `predictions_file`: The predictions for the images in `predict_images_file`.

Usage: python training_runner.py <config.json>
"""

from __future__ import annotations

import json
import sys
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

import lightly_train  # type: ignore[import-not-found]
import torch

_PREDICTION_BATCH_SIZE = 8


def main(config_path: Path) -> None:
    """Train a model, then write its predictions for all images in the config."""
    config = json.loads(config_path.read_text(encoding="utf-8"))
    out_dir = Path(config["out_dir"])
    _write_stage(config=config, stage="training")
    lightly_train.train_object_detection(
        out=str(out_dir),
        model=config["model_name"],
        data={
            "format": "coco",
            "train": {"annotations": config["train_annotations_file"]},
            "val": {"annotations": config["val_annotations_file"]},
        },
        steps=config["steps"],
        precision=_precision(),
        logger_args={"log_every_num_steps": max(1, config["steps"] // 50)},
    )

    _write_stage(config=config, stage="predicting")
    model = lightly_train.load_model(str(_exported_model_path(out_dir=out_dir)))
    images = json.loads(Path(config["predict_images_file"]).read_text(encoding="utf-8"))
    predictions = _predict(model=model, images=images, threshold=config["score_threshold"])
    Path(config["predictions_file"]).write_text(json.dumps(predictions), encoding="utf-8")


def _write_stage(config: dict[str, Any], stage: str) -> None:
    Path(config["stage_file"]).write_text(stage, encoding="utf-8")


def _precision() -> str:
    # Mixed precision needs a GPU. On the CPU and on MPS full precision is used.
    return "bf16-mixed" if torch.cuda.is_available() else "32-true"


def _exported_model_path(out_dir: Path) -> Path:
    # The best model is saved only after a validation round improves the metric.
    exported_dir = out_dir / "exported_models"
    best_path = exported_dir / "exported_best.pt"
    return best_path if best_path.exists() else exported_dir / "exported_last.pt"


def _predict(
    model: Any, images: Sequence[dict[str, str]], threshold: float
) -> list[dict[str, Any]]:
    """Predict boxes for images given as `{"sample_id": ..., "path": ...}` entries."""
    predictions: list[dict[str, Any]] = []
    for batch in _batches(items=images, size=_PREDICTION_BATCH_SIZE):
        results = model.predict_batch([image["path"] for image in batch], threshold=threshold)
        for image, result in zip(batch, results):
            detections = [
                {
                    "class_name": model.classes[int(label)],
                    "bbox_xyxy": [float(value) for value in box.tolist()],
                    "score": float(score),
                }
                for box, label, score in zip(result["bboxes"], result["labels"], result["scores"])
            ]
            predictions.append({"sample_id": image["sample_id"], "detections": detections})
    return predictions


def _batches(items: Sequence[dict[str, str]], size: int) -> Iterator[Sequence[dict[str, str]]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


if __name__ == "__main__":
    main(config_path=Path(sys.argv[1]))
