"""Command line interface for LightlyStudio."""

from __future__ import annotations

from importlib import metadata

import click

import lightly_studio
from lightly_studio.database import db_manager


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
    """Launch the GUI preloaded with the COCO demo dataset."""
    import lightly_studio as ls

    dataset_path = ls.utils.download_example_dataset(
        download_dir="dataset_examples",
        force_redownload=force_download,
    )
    db_manager.connect(cleanup_existing=True)
    dataset = ls.ImageDataset.create()
    dataset.add_samples_from_coco(
        annotations_json=f"{dataset_path}/coco_subset_128_images/instances_train2017.json",
        images_path=f"{dataset_path}/coco_subset_128_images/images",
        annotation_type=ls.AnnotationType.SEGMENTATION_MASK,
    )
    ls.start_gui(port=port)


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
