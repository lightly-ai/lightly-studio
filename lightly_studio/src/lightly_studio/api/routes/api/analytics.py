"""This module contains the API routes for analytics identity."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from lightly_studio.analytics import cohort, install_id, posthog_project
from lightly_studio.dataset.env import (
    LIGHTLY_STUDIO_ANALYTICS_ENABLED,
    LIGHTLY_STUDIO_POSTHOG_HOST,
)
from lightly_studio.errors import NotFoundError

__all__ = ["analytics_router"]

analytics_router = APIRouter(tags=["analytics"])


class AnalyticsConfig(BaseModel):
    """What the web app needs to report to the same place as the Python SDK.

    Attributes:
        install_id: The anonymous install id shared across the analytics SDKs.
        posthog_key: Project API key to report against. Only the backend can tell a checkout from
            a released package, so the project is decided here for both SDKs.
        posthog_host: PostHog instance to report to.
    """

    install_id: str
    posthog_key: str
    posthog_host: str


@analytics_router.get("/analytics/config")
def get_analytics_config() -> AnalyticsConfig:
    """Get the analytics configuration the web app reports under.

    The web app identifies with the install id, so browser and Python events land under one
    distinct id per install, and initialises PostHog with the key, so both reach one project.

    Raises:
        NotFoundError: If usage tracking is switched off.
    """
    # Opting out must leave no id on disk, so refuse before get_install_id() creates one.
    if not LIGHTLY_STUDIO_ANALYTICS_ENABLED:
        raise NotFoundError("Usage tracking is disabled.")

    return AnalyticsConfig(
        install_id=str(install_id.get_install_id()),
        posthog_key=posthog_project.get_project_key(cohort.get_cohort()),
        posthog_host=LIGHTLY_STUDIO_POSTHOG_HOST,
    )
