"""Helpers to render and create LightlyTrain scripts."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from jinja2 import Environment

from lightly_studio.core.dataset_query import ImageSampleField
from lightly_studio.core.image.image_dataset import ImageDataset

LOGGER = logging.getLogger(__name__)

TRAIN_OBJECT_DETECTION_TEMPLATE_PATH = (
    Path(__file__).resolve().parent / "train_object_detection.jinja2"
)


def update_train_object_detection_template(
    template_values: Mapping[str, Any],
) -> str:
    """Render the object detection training template.

    Args:
        template_values: Values injected into the Jinja template.

    Returns:
        The rendered training script as a string.
    """
    template_text = TRAIN_OBJECT_DETECTION_TEMPLATE_PATH.read_text(encoding="utf-8")
    template = Environment().from_string(template_text)
    return template.render(**template_values)


def create_train_object_detection_script(
    template_values: Mapping[str, Any],
    output_script_path: str | Path,
) -> Path:
    """Render and persist an object detection training script.

    Args:
        template_values: Values injected into the template.
        output_script_path: Output path of the generated Python script.

    Returns:
        The path to the generated script file.
    """
    rendered_script = update_train_object_detection_template(
        template_values=template_values,
    )
    output_path = Path(output_script_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered_script, encoding="utf-8")
    LOGGER.info("Generated LightlyTrain script at: %s", output_path)
    return output_path


def lt_train_script(
    dataset: ImageDataset,
    output_dir: str | Path,
    train_tag_name: str = "train",
    val_tag_name: str = "val",
) -> Path:
    """Generate a LightlyTrain object detection script from tagged splits.

    The function exports two COCO annotation files from the input dataset:
    one for `train_tag_name` and one for `val_tag_name`. It then renders
    `train_object_detection.jinja2` with the generated annotation paths and
    writes the resulting Python training script to `./output`.

    Args:
        dataset: Dataset that contains the split tags.
        output_dir: Directory where exported COCO files and the generated
            training script are written.
        train_tag_name: Tag name used for selecting training samples.
        val_tag_name: Tag name used for selecting validation samples.

    Returns:
        The path to the generated training script.
    """
    resolved_output_dir = Path(output_dir).resolve()
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    train_annotations_path = resolved_output_dir / f"{train_tag_name}_coco.json"
    val_annotations_path = resolved_output_dir / f"{val_tag_name}_coco.json"

    _export_coco_for_tag(
        dataset=dataset,
        tag_name=train_tag_name,
        output_json_path=train_annotations_path,
    )
    _export_coco_for_tag(
        dataset=dataset,
        tag_name=val_tag_name,
        output_json_path=val_annotations_path,
    )

    template_values: dict[str, Any] = {
        "train_annotations": train_annotations_path.as_posix(),
        "val_annotations": val_annotations_path.as_posix(),
    }

    output_script_path = resolved_output_dir / "train_object_detection.py"

    return create_train_object_detection_script(
        template_values=template_values,
        output_script_path=output_script_path,
    )


def _export_coco_for_tag(
    dataset: ImageDataset,
    tag_name: str,
    output_json_path: Path,
) -> None:
    """Export COCO object detection annotations for one tag.

    Args:
        dataset: Source dataset to export from.
        tag_name: Tag used to filter samples before export.
        output_json_path: Destination path of the COCO JSON file.
    """
    query = dataset.query().match(ImageSampleField.tags.contains(tag_name))
    dataset.export(query).to_coco_object_detections(output_json=output_json_path)
    LOGGER.info("Exported COCO annotations for tag '%s' to %s", tag_name, output_json_path)
