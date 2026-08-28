"""This module contains the API routes for analytics identity."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from lightly_studio.analytics import install_id

__all__ = ["analytics_router"]

analytics_router = APIRouter(tags=["analytics"])


class InstallId(BaseModel):
    """The anonymous install id shared across the analytics SDKs."""

    install_id: str


@analytics_router.get("/install_id")
def get_install_id() -> InstallId:
    """Get the anonymous install id.

    The web app calls PostHog's identify() with this id so that browser events
    and the Python SDK's events land under one distinct id per install.
    """
    return InstallId(install_id=str(install_id.get_install_id()))
