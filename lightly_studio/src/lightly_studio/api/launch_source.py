"""Tracks which entry point started the running LightlyStudio app."""

from __future__ import annotations

from enum import Enum
from uuid import UUID, uuid4


class LaunchSource(str, Enum):
    """The entry point that started the running LightlyStudio app."""

    QUICKSTART = "quickstart"
    GUI = "gui"
    SDK = "sdk"


# Defaults to SDK because `lightly_studio.start_gui()` can be called directly from a script or
# notebook, without going through the CLI.
_launch_source: LaunchSource = LaunchSource.SDK

# Identifies this process. This module is imported once per process, so every run of the app gets
# its own ID and the GUI can report a launch exactly once, however often the page is reloaded.
_launch_id: UUID = uuid4()


def get_launch_source() -> LaunchSource:
    """Get the entry point that started the running app."""
    return _launch_source


def get_launch_id() -> UUID:
    """Get the ID identifying the running app process."""
    return _launch_id


def set_launch_source(source: LaunchSource) -> None:
    """Record the entry point that started the running app.

    Args:
        source: The entry point to record.
    """
    global _launch_source  # noqa: PLW0603
    _launch_source = source
