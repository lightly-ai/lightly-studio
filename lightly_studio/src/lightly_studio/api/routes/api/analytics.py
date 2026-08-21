"""This module contains the API routes for the analytics configuration."""

from __future__ import annotations

from fastapi import APIRouter

from lightly_studio.api import analytics_config
from lightly_studio.api.analytics_config import AnalyticsConfigView

__all__ = ["analytics_router"]

analytics_router = APIRouter()


@analytics_router.get("/analytics/config")
def get_analytics_config() -> AnalyticsConfigView:
    """Get the analytics configuration the GUI reports under."""
    return analytics_config.get_analytics_config()
