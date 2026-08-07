"""Command line interface for LightlyStudio."""

from __future__ import annotations

from importlib import metadata
from pathlib import Path

import click

import lightly_studio
from lightly_studio.database import db_manager
from lightly_studio.evaluation.image_dataset_evaluate import ObjectDetectionEvaluationConfig


@click.group()
@click.version_option(version=metadata.version("lightly-studio"), prog_name="lightly-studio")
def main() -> None:
    """LightlyStudio CLI."""


@main.command()
@click.option("--port", default=None, type=int, help="Port to bind the server to.")
@click.option(
    "--force-download",
    is_flag=True,
    default=False,
    help="Re-download the demo dataset even if already cached.",
)
@click.option(
    "--no-browser",
    is_flag=True,
    default=False,
    help="Do not open a browser automatically once the GUI server is ready.",
)
def quickstart(port: int | None, force_download: bool, no_browser: bool) -> None:
    """Launch the GUI preloaded with a COCO object detection evaluation demo dataset.

    Recreates ./quickstart.db in the current directory on every run, overwriting
    any existing file with that name.
    """
    coco_dir, images_path = _download_quickstart_dataset(force_download=force_download)
    db_manager.connect(db_file="quickstart.db", cleanup_existing=True)
    dataset = _load_quickstart_dataset(coco_dir=coco_dir, images_path=images_path)
    _evaluate_quickstart_dataset(dataset=dataset)
    lightly_studio.start_gui(port=port, open_browser=not no_browser)


@main.command()
@click.option("--host", default=None, type=str, help="Host to bind the server to.")
@click.option("--port", default=None, type=int, help="Port to bind the server to.")
@click.option(
    "--db-file",
    default=None,
    type=str,
    help="Path to DuckDB file, e.g. 'lightly_studio.db'. Mutually exclusive with --db-url.",
)
@click.option(
    "--db-url",
    default=None,
    type=str,
    help=(
        "Full database URL, e.g. 'duckdb:///lightly_studio.db'. Mutually exclusive with --db-file."
    ),
)
def gui(
    host: str | None,
    port: int | None,
    db_file: str | None,
    db_url: str | None,
) -> None:
    """Start the web interface."""
    if db_file is not None and db_url is not None:
        raise click.UsageError("Options '--db-file' and '--db-url' are mutually exclusive.")
    db_manager.connect(db_file=db_file, db_url=db_url, must_exist=True)
    lightly_studio.start_gui(host=host, port=port)


def _download_quickstart_dataset(force_download: bool) -> tuple[Path, Path]:
    """Download the demo COCO dataset and return (coco_dir, images_path)."""
    dataset_path = Path(
        lightly_studio.utils.download_example_dataset(
            download_dir="dataset_examples",
            force_redownload=force_download,
        )
    )
    coco_dir = dataset_path / "coco_subset_128_images"
    return coco_dir, coco_dir / "images"


def _load_quickstart_dataset(coco_dir: Path, images_path: Path) -> lightly_studio.ImageDataset:
    """Create the quickstart dataset and import its ground-truth and prediction annotations."""
    dataset = lightly_studio.ImageDataset.create()
    dataset.add_images_from_path(path=images_path)
    dataset.add_annotations_from_coco(
        annotations_json=coco_dir / "instances_train2017.json",
        images_root=images_path,
        annotation_source="ground_truth",
    )
    dataset.add_annotations_from_coco(
        annotations_json=coco_dir / "predictions_train2017.json",
        images_root=images_path,
        annotation_source="predictions",
    )
    # Tag a subset of samples to demonstrate tags in the GUI.
    dataset.query()[:10].add_tag("sample_subset")
    return dataset


def _evaluate_quickstart_dataset(dataset: lightly_studio.ImageDataset) -> None:
    """Run the object-detection evaluation used to showcase the evaluation GUI."""
    evaluation_config = ObjectDetectionEvaluationConfig(
        iou_threshold=0.5,
        classwise=False,
    )
    dataset.evaluate().object_detection(
        name="od_evaluation",
        gt_annotation_source="ground_truth",
        pred_annotation_source="predictions",
        config=evaluation_config,
    )
