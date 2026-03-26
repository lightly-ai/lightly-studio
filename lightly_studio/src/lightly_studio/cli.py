"""Command line interface for LightlyStudio."""

from __future__ import annotations

from importlib import metadata

import click

import lightly_studio
from lightly_studio import db_manager


@click.group()
@click.version_option(version=metadata.version("lightly-studio"), prog_name="lightly-studio")
def main() -> None:
    """LightlyStudio CLI."""


@main.command()
@click.option("--host", default=None, type=str, help="Host to bind the server to.")
@click.option("--port", default=None, type=int, help="Port to bind the server to.")
@click.option("--db-file", default=None, type=str, help="Path to DuckDB file, e.g. 'lightly_studio.db'. Mutually exclusive with --db-url.")
@click.option("--db-url", default=None, type=str, help="Full database URL, e.g. 'duckdb:///lightly_studio.db'. Mutually exclusive with --db-file.")
def gui(
    host: str | None,
    port: int | None,
    db_file: str | None,
    db_url: str | None,
) -> None:
    """Start the web interface."""
    if db_file is not None and db_url is not None:
        raise click.UsageError(
            "Options '--db-file' and '--db-url' are mutually exclusive."
        )
    db_manager.connect(db_file=db_file, engine_url=db_url)
    lightly_studio.start_gui(host=host, port=port)
