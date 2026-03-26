"""Command line interface for LightlyStudio."""

from __future__ import annotations

from importlib import metadata

import click

import lightly_studio


@click.group()
@click.version_option(version=metadata.version("lightly-studio"), prog_name="lightly-studio")
def main() -> None:
    """LightlyStudio CLI."""


@main.command()
@click.option("--host", default=None, type=str, help="Host to bind the server to.")
@click.option("--port", default=None, type=int, help="Port to bind the server to.")
def gui(host: str | None, port: int | None) -> None:
    """Start the web interface."""
    lightly_studio.start_gui(host=host, port=port)
