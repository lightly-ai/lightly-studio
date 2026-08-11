"""This module contains the API route for the app launch source."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from lightly_studio.api import launch_source
from lightly_studio.api.launch_source import LaunchSource

launch_source_router = APIRouter(tags=["launch_source"])


class LaunchSourceInfo(BaseModel):
    """The entry point that started the running LightlyStudio app."""

    launch_source: LaunchSource


@launch_source_router.get("/launch-source")
def get_launch_source() -> LaunchSourceInfo:
    """Get the entry point that started the running app."""
    return LaunchSourceInfo(launch_source=launch_source.get_launch_source())
