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
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import lightly_train  # type: ignore[import-not-found]
import torch

_TRAIN_BATCH_SIZE = 16
# Train without data augmentation. Without scale jitter, all images are resized to the input
# size of the model, so that the images of a batch have the same size.
_TRAIN_TRANSFORM_ARGS: dict[str, Any] = {
    "photometric_distort": None,
    "random_zoom_out": None,
    "random_iou_crop": None,
    "random_flip": None,
    "scale_jitter": None,
    "resize": {"height": "auto", "width": "auto"},
}
# The Lightning accelerator name for each torch device type.
_ACCELERATORS = {"cuda": "gpu", "mps": "mps", "cpu": "cpu"}


def main(config_path: Path) -> None:
    """Train a model, then write its predictions for all images in the config."""
    config = json.loads(config_path.read_text(encoding="utf-8"))
    out_dir = Path(config["out_dir"])
    device = _device()
    print(f"Training and predicting on device '{device}'.", flush=True)
    _write_stage(config=config, stage="training")
    lightly_train.train_object_detection(
        out=str(out_dir),
        model=config["model_name"],
        # With a checkpoint, LightlyTrain starts from its weights instead of the COCO weights.
        checkpoint=_start_checkpoint(config=config),
        data={
            "format": "coco",
            "train": {"annotations": config["train_annotations_file"]},
            "val": {"annotations": config["val_annotations_file"]},
        },
        steps=config["steps"],
        batch_size=_TRAIN_BATCH_SIZE,
        transform_args=_TRAIN_TRANSFORM_ARGS,
        accelerator=_ACCELERATORS[device],
        # One device only. With more GPUs, LightlyTrain starts more processes, and Studio
        # cancels a run by stopping only this process.
        devices=1,
        precision=_precision(device=device),
        logger_args={"log_every_num_steps": max(1, config["steps"] // 50)},
    )

    _write_stage(config=config, stage="predicting")
    model = lightly_train.load_model(
        model=str(_exported_model_path(out_dir=out_dir)), device=device
    )
    images = json.loads(Path(config["predict_images_file"]).read_text(encoding="utf-8"))
    predictions = _predict(model=model, images=images, threshold=config["score_threshold"])
    Path(config["predictions_file"]).write_text(json.dumps(predictions), encoding="utf-8")


def _start_checkpoint(config: dict[str, Any]) -> str | None:
    """Return the model to start training from, or None to start from the COCO weights.

    If the classes of the start model are not the classes of the train annotations, the
    class head of the start model does not fit. Then this function writes a copy of the
    start model without the class head, so that LightlyTrain initializes a new class head
    and keeps the other weights.
    """
    start_model_file = config["start_model_file"]
    if start_model_file is None:
        return None
    checkpoint = torch.load(start_model_file, map_location="cpu", weights_only=False)
    if _classes_match(
        checkpoint=checkpoint, train_annotations_file=Path(config["train_annotations_file"])
    ):
        print(f"Starting from the model '{start_model_file}'.", flush=True)
        return str(start_model_file)

    # The PicoDet class head layers have "gfl_cls" in their names.
    checkpoint["train_model"] = {
        key: value for key, value in checkpoint["train_model"].items() if ".gfl_cls." not in key
    }
    torch.save(checkpoint, config["start_model_copy_file"])
    print(
        f"Starting from the model '{start_model_file}' with a new class head, "
        "because the classes changed.",
        flush=True,
    )
    return str(config["start_model_copy_file"])


def _classes_match(checkpoint: dict[str, Any], train_annotations_file: Path) -> bool:
    """Return whether the model has the same classes as the train annotations.

    The model has its classes in `checkpoint["model_init_args"]["classes"]`, a dict from
    the class ID to the class name, for example `{0: "animal", 1: "human"}`. The COCO
    file has its classes in "categories", a list of `{"id": ..., "name": ...}` entries.
    """
    model_classes = checkpoint.get("model_init_args", {}).get("classes")
    if model_classes is None:
        return False
    coco = json.loads(train_annotations_file.read_text(encoding="utf-8"))
    # Compare the full mapping from class ID to name, because a new class can shift the IDs
    # of the other classes.
    train_classes = {int(c["id"]): str(c["name"]) for c in coco["categories"]}
    return {int(k): str(v) for k, v in model_classes.items()} == train_classes


def _write_stage(config: dict[str, Any], stage: str) -> None:
    Path(config["stage_file"]).write_text(stage, encoding="utf-8")


def _device() -> str:
    """Return the fastest available device: a CUDA GPU, then Apple MPS, then the CPU."""
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _precision(device: str) -> str:
    # bf16 has the range of fp32, so it needs no gradient scaler. CUDA GPUs older than
    # Ampere have no bf16 and use fp16. The CPU uses full precision, because bf16 is often
    # not faster there.
    if device == "cuda":
        return "bf16-mixed" if torch.cuda.is_bf16_supported() else "16-mixed"
    if device == "mps":
        return "bf16-mixed"
    return "32-true"


def _exported_model_path(out_dir: Path) -> Path:
    # The best model is saved only after a validation round improves the metric.
    exported_dir = out_dir / "exported_models"
    best_path = exported_dir / "exported_best.pt"
    return best_path if best_path.exists() else exported_dir / "exported_last.pt"


def _predict(
    model: Any, images: Sequence[dict[str, str]], threshold: float
) -> list[dict[str, Any]]:
    """Predict boxes for images given as `{"sample_id": ..., "path": ...}` entries.

    The prediction is one image at a time, because PicoDet has no batch prediction.
    """
    predictions: list[dict[str, Any]] = []
    for image in images:
        result = model.predict(image["path"], threshold=threshold)
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


if __name__ == "__main__":
    main(config_path=Path(sys.argv[1]))
