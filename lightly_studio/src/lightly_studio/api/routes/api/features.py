"""This module contains the API routes for active features."""

from __future__ import annotations

from fastapi import APIRouter

from lightly_studio.api.features import lightly_studio_active_features

__all__ = ["features_router", "lightly_studio_active_features"]

features_router = APIRouter()


# TODO(Michal, 12/2025): Features are currently unused. Remove the endpoint if still not used
# in a couple of months.
@features_router.get("/features")
def get_features() -> list[str]:
    """Get the list of active features in the LightlyStudio app."""
    return lightly_studio_active_features
