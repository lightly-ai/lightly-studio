"""Command line interface for LightlyStudio."""

from __future__ import annotations

from importlib import metadata
from pathlib import Path

import click

import lightly_studio
from lightly_studio.analytics import tracking
from lightly_studio.analytics.tracking import LaunchSource
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
    """Launch the GUI preloaded with a COCO object detection evaluation demo dataset."""
    dataset_path = Path(
        lightly_studio.utils.download_example_dataset(
            download_dir="dataset_examples",
            force_redownload=force_download,
        )
    )
    coco_dir = dataset_path / "coco_subset_128_images"
    images_path = coco_dir / "images"
    evaluation_config = ObjectDetectionEvaluationConfig(
        iou_threshold=0.5,
        classwise=False,
    )

    db_manager.connect(db_file="quickstart.db", cleanup_existing=True)
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
    dataset.evaluate().object_detection(
        name="od_evaluation",
        gt_annotation_source="ground_truth",
        pred_annotation_source="predictions",
        config=evaluation_config,
    )

    tracking.track(
        event=tracking.APP_LAUNCHED,
        properties={"launch_source": LaunchSource.QUICKSTART.value},
    )
    lightly_studio.start_gui(port=port, open_browser=not no_browser)


@main.command()
@click.option(
    "--api-url",
    default=None,
    type=str,
    envvar="LIGHTLY_STUDIO_API_URL",
    help="Base URL of the enterprise instance, e.g. 'http://10.0.0.5:8100'.",
)
@click.option(
    "--token",
    default=None,
    type=str,
    envvar="LIGHTLY_STUDIO_TOKEN",
    help="JWT token from the enterprise GUI.",
)
@click.option(
    "--api-key",
    default=None,
    type=str,
    envvar="LIGHTLY_STUDIO_API_KEY",
    help="API key from the enterprise GUI.",
)
def quickstart_enterprise(api_url: str | None, token: str | None, api_key: str | None) -> None:
    """Seed a remote enterprise instance with a COCO object detection evaluation demo dataset."""
    data_root = "hf://datasets/lightly-ai/coco_subset_128_images"
    evaluation_config = ObjectDetectionEvaluationConfig(
        iou_threshold=0.5,
        classwise=False,
    )

    lightly_studio.connect(api_url=api_url, token=token, api_key=api_key)
    dataset = lightly_studio.ImageDataset.load_or_create(name="example-coco-128")
    has_samples = bool(dataset.query().to_list())
    if has_samples and _has_evaluation(dataset=dataset, name="od_evaluation"):
        click.echo("Dataset 'example-coco-128' is already seeded, skipping.")
        return
    if has_samples:
        raise click.ClickException(
            "Dataset 'example-coco-128' is partially seeded from an earlier failed run. "
            "Delete it in the GUI and run the command again."
        )
    dataset.add_images_from_path(path=f"{data_root}/images")
    dataset.add_annotations_from_coco(
        annotations_json=f"{data_root}/instances_train2017.json",
        images_root=f"{data_root}/images",
        annotation_source="ground_truth",
    )
    dataset.add_annotations_from_coco(
        annotations_json=f"{data_root}/predictions_train2017.json",
        images_root=f"{data_root}/images",
        annotation_source="predictions",
    )
    # Tag a subset of samples to demonstrate tags in the GUI.
    dataset.query()[:10].add_tag("sample_subset")
    dataset.evaluate().object_detection(
        name="od_evaluation",
        gt_annotation_source="ground_truth",
        pred_annotation_source="predictions",
        config=evaluation_config,
    )

    tracking.track(
        event=tracking.APP_LAUNCHED,
        properties={"launch_source": LaunchSource.QUICKSTART_ENTERPRISE.value},
    )


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
    tracking.track(
        event=tracking.APP_LAUNCHED,
        properties={"launch_source": LaunchSource.GUI.value},
    )
    lightly_studio.start_gui(host=host, port=port)


def _has_evaluation(dataset: lightly_studio.ImageDataset, name: str) -> bool:
    return any(run.name == name for run in dataset.evaluate().list_runs())
