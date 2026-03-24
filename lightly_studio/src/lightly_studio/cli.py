"""Command line interface for LightlyStudio."""

from importlib.metadata import version

import click

from lightly_studio import start_gui


@click.group()
@click.version_option(version=version("lightly-studio"), prog_name="lightly-studio")
def main() -> None:
    """LightlyStudio CLI."""


@main.command()
def gui() -> None:
    """Start the web interface."""
    start_gui()
