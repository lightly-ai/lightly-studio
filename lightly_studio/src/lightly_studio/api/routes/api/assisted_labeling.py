"""API routes for assisted labeling."""

from __future__ import annotations

import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID

from fastapi import APIRouter

from lightly_studio.assisted_labeling import fal_sam3_provider
from lightly_studio.assisted_labeling.provider import ProviderImage
from lightly_studio.database import db_manager
from lightly_studio.models.assisted_labeling import (
    AssistedLabelingStatusView,
    InstancesAnnotationRequest,
    InstancesAnnotationResponse,
    InteractiveAnnotationRequest,
    InteractiveAnnotationResponse,
)
from lightly_studio.services import assisted_labeling_service
from lightly_studio.utils import executor

assisted_labeling_router = APIRouter(prefix="/annotate", tags=["annotate"])

PROVIDER_MAX_WORKERS = 8


@assisted_labeling_router.get("/status")
def get_assisted_labeling_status() -> AssistedLabelingStatusView:
    """Returns whether assisted labeling is usable."""
    return AssistedLabelingStatusView(
        unavailable_reason=fal_sam3_provider.get_provider().unavailable_reason()
    )


@assisted_labeling_router.post("/interactive")
async def create_interactive_annotation_preview(
    request: InteractiveAnnotationRequest,
) -> InteractiveAnnotationResponse:
    """Returns a single-object preview from points or boxes. Saves nothing."""
    return await asyncio.get_running_loop().run_in_executor(
        _get_provider_executor(), functools.partial(_create_interactive_preview, request=request)
    )


@annotate_router.post("/instances")
async def create_instances_annotation_preview(
    request: InstancesAnnotationRequest,
) -> InstancesAnnotationResponse:
    """Returns previews of all instances that match a text prompt or boxes. Saves nothing."""
    return await asyncio.get_running_loop().run_in_executor(
        _get_provider_executor(), functools.partial(_create_instances_preview, request=request)
    )


def _get_provider_executor() -> ThreadPoolExecutor:
    return executor.get_media_executor(
        thread_name_prefix="assisted_labeling", max_workers=PROVIDER_MAX_WORKERS
    )


def _create_interactive_preview(
    request: InteractiveAnnotationRequest,
) -> InteractiveAnnotationResponse:
    image = _load_image(collection_id=request.collection_id, sample_id=request.sample_id)
    return assisted_labeling_service.create_interactive_preview(
        provider=fal_sam3_provider.get_provider(), image=image, request=request
    )


def _create_instances_preview(
    request: InstancesAnnotationRequest,
) -> InstancesAnnotationResponse:
    image = _load_image(collection_id=request.collection_id, sample_id=request.sample_id)
    return assisted_labeling_service.create_instances_preview(
        provider=fal_sam3_provider.get_provider(), image=image, request=request
    )


def _load_image(collection_id: UUID, sample_id: UUID) -> ProviderImage:
    # No SessionDep: the session closes before the slow provider call.
    with db_manager.session() as session:
        return assisted_labeling_service.load_provider_image(
            session=session, collection_id=collection_id, sample_id=sample_id
        )
