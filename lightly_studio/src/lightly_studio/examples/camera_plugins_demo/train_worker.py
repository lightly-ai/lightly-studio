"""Subprocess entry point that trains an object detector with LightlyTrain.

Training runs in its own process so that the LightlyStudio server stays responsive and
so that LightlyTrain's global logging setup and dataloader workers stay isolated.

Usage:
    python -m lightly_studio.examples.camera_plugins_demo.train_worker <run.json>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import lightly_train  # type: ignore[import-not-found]


def main(config_path: Path) -> None:
    """Train an object detector from a run configuration file."""
    config: dict[str, Any] = json.loads(config_path.read_text())
    image_size = int(config["image_size"])
    steps = int(config["steps"])
    lightly_train.train_object_detection(
        out=config["out"],
        overwrite=True,
        data={
            "format": "coco",
            "train": {"annotations": config["train_annotations"]},
            "val": {"annotations": config["val_annotations"]},
            "skip_if_annotations_missing": True,
        },
        model=config["model"],
        steps=steps,
        batch_size=int(config["batch_size"]),
        num_workers=int(config["num_workers"]),
        accelerator=config["accelerator"],
        devices=1,
        precision=config["precision"],
        # Keep one optimizer step per batch. The model defaults accumulate gradients up
        # to a COCO-scale batch size, which makes every logged step very slow.
        gradient_accumulation_steps=1,
        transform_args={"image_size": (image_size, image_size)},
        model_args=_schedule_args(steps=steps),
    )


def _schedule_args(steps: int) -> dict[str, int]:
    """Return learning-rate schedule bounds that hold for a short fine-tuning run.

    The "auto" schedule of LT-DETR is derived from the COCO recipe. On a run of a few
    epochs it puts the end of the flat phase on the start of the no-augmentation tail,
    which leaves the cosine phase empty and stops training with a ValueError. These
    bounds keep every phase non-empty for any step count.
    """
    warmup_steps = max(1, round(steps * 0.1))
    no_aug_steps = max(1, round(steps * 0.1))
    flat_steps = min(max(round(steps * 0.5), warmup_steps + 1), steps - no_aug_steps - 1)
    return {
        "lr_warmup_steps": warmup_steps,
        "scheduler_flat_steps": flat_steps,
        "scheduler_no_aug_steps": no_aug_steps,
    }


_EXPECTED_ARGUMENT_COUNT = 2

if __name__ == "__main__":
    # The __main__ guard is required: dataloader workers re-import this module.
    if len(sys.argv) != _EXPECTED_ARGUMENT_COUNT:
        raise SystemExit("Usage: python -m ...train_worker <run.json>")
    main(config_path=Path(sys.argv[1]))
