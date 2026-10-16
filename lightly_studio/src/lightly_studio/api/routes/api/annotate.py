"""API routes for assisted labeling."""

from __future__ import annotations

from fastapi import APIRouter

from lightly_studio.models.assisted_labeling import AssistedLabelingProviderView
from lightly_studio.services import assisted_labeling_service

annotate_router = APIRouter(prefix="/annotate", tags=["annotate"])


@annotate_router.get("/providers")
def list_assisted_labeling_providers() -> list[AssistedLabelingProviderView]:
    """Returns all providers."""
    return assisted_labeling_service.list_provider_views()
