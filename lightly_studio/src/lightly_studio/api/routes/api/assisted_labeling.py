"""API routes for assisted labeling."""

from __future__ import annotations

from fastapi import APIRouter

from lightly_studio.assisted_labeling import fal_sam3_provider
from lightly_studio.models.assisted_labeling import AssistedLabelingStatusView

assisted_labeling_router = APIRouter(prefix="/annotate", tags=["annotate"])


@assisted_labeling_router.get("/status")
def get_assisted_labeling_status() -> AssistedLabelingStatusView:
    """Returns whether assisted labeling is usable."""
    return AssistedLabelingStatusView(
        unavailable_reason=fal_sam3_provider.get_provider().unavailable_reason()
    )
