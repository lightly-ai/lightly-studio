"""Command line interface for LightlyStudio."""

from __future__ import annotations

from importlib import metadata

import click

import lightly_studio
from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
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
def demo(port: int | None, force_download: bool) -> None:
    """Launch the GUI preloaded with a COCO object detection evaluation demo dataset."""
    dataset_path = lightly_studio.utils.download_example_dataset(
        download_dir="dataset_examples",
        force_redownload=force_download,
    )
    images_path = f"{dataset_path}/coco_subset_128_images/images"
    evaluation_config = ObjectDetectionEvaluationConfig(
        iou_threshold=0.5,
        classwise=True,
    )

    db_manager.connect(db_file="demo.db", cleanup_existing=force_download)
    dataset = lightly_studio.ImageDataset.load_or_create()
    dataset.add_images_from_path(path=images_path)
    dataset.add_annotations_from_coco(
        annotations_json=f"{dataset_path}/coco_subset_128_images/instances_train2017.json",
        images_root=images_path,
        annotation_source="ground_truth",
    )
    dataset.add_annotations_from_coco(
        annotations_json=f"{dataset_path}/coco_subset_128_images/predictions_train2017.json",
        images_root=images_path,
        annotation_source="predictions",
    )
    # Tag a subset of samples to run the evaluation on.
    dataset.query()[:10].add_tag("evaluated_samples")
    tagged_evaluation_query = dataset.query().match(
        ImageSampleField.tags.contains("evaluated_samples")
    )
    dataset.evaluate(query=tagged_evaluation_query).object_detection(
        name="od_evaluation",
        gt_annotation_source="ground_truth",
        pred_annotation_source="predictions",
        config=evaluation_config,
    )

    lightly_studio.start_gui(port=port)


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
