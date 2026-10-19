"""API routes for assisted labeling."""

from __future__ import annotations

import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter

from lightly_studio.assisted_labeling import fal_sam3_provider
from lightly_studio.database import db_manager
from lightly_studio.models.assisted_labeling import (
    AssistedLabelingStatusView,
    InteractiveAnnotationRequest,
    InteractiveAnnotationResponse,
)
from lightly_studio.services import assisted_labeling_service

assisted_labeling_router = APIRouter(prefix="/annotate", tags=["annotate"])

PROVIDER_MAX_WORKERS = 8


@assisted_labeling_router.get("/status")
def get_assisted_labeling_status() -> AssistedLabelingStatusView:
    """Returns whether assisted labeling is usable."""
    return AssistedLabelingStatusView(
        unavailable_reason=fal_sam3_provider.get_provider().unavailable_reason()
    )


@annotate_router.post("/interactive")
async def create_interactive_annotation_preview(
    request: InteractiveAnnotationRequest,
) -> InteractiveAnnotationResponse:
    """Returns a single-object preview from points or boxes. Saves nothing."""
    return await asyncio.get_running_loop().run_in_executor(
        _get_provider_executor(), functools.partial(_create_interactive_preview, request=request)
    )


@functools.cache
def _get_provider_executor() -> ThreadPoolExecutor:
    return ThreadPoolExecutor(
        max_workers=PROVIDER_MAX_WORKERS, thread_name_prefix="assisted_labeling"
    )


def _create_interactive_preview(
    request: InteractiveAnnotationRequest,
) -> InteractiveAnnotationResponse:
    # No SessionDep: the session closes before the slow provider call.
    with db_manager.session() as session:
        image = assisted_labeling_service.load_provider_image(
            session=session, collection_id=request.collection_id, sample_id=request.sample_id
        )
    return assisted_labeling_service.create_interactive_preview(
        provider=fal_sam3_provider.get_provider(), image=image, request=request
    )
