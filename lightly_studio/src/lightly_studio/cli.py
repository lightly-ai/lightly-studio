from importlib.metadata import version

import click


@click.group()
@click.version_option(version=version("lightly-studio"), prog_name="lightly-studio")
def main() -> None:
    """LightlyStudio CLI."""


@main.command()
def gui() -> None:
    """Start the web interface."""
    from lightly_studio import start_gui

    start_gui()
