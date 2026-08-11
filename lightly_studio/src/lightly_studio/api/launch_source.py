"""Tracks which entry point started the running LightlyStudio app."""

from __future__ import annotations

from enum import Enum


class LaunchSource(str, Enum):
    """The entry point that started the running LightlyStudio app."""

    QUICKSTART = "quickstart"
    GUI = "gui"
    SDK = "sdk"


# Defaults to SDK because `lightly_studio.start_gui()` can be called directly from a script or
# notebook, without going through the CLI.
_launch_source: LaunchSource = LaunchSource.SDK


def get_launch_source() -> LaunchSource:
    """Get the entry point that started the running app."""
    return _launch_source


def set_launch_source(source: LaunchSource) -> None:
    """Record the entry point that started the running app.

    Args:
        source: The entry point to record.
    """
    global _launch_source  # noqa: PLW0603
    _launch_source = source
