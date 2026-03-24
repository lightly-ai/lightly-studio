"""Command line interface for LightlyStudio."""

from importlib import metadata

import click

import lightly_studio


@click.group()
@click.version_option(version=metadata.version("lightly-studio"), prog_name="lightly-studio")
def main() -> None:
    """LightlyStudio CLI."""


@main.command()
def gui() -> None:
    """Start the web interface."""
    lightly_studio.start_gui()
