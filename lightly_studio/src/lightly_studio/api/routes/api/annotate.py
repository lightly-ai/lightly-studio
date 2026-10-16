"""API routes for assisted labeling."""

from __future__ import annotations

import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID

from fastapi import APIRouter

from lightly_studio.assisted_labeling.provider import AssistedLabelingProvider, ProviderImage
from lightly_studio.database import db_manager
from lightly_studio.models.assisted_labeling import (
    AssistedLabelingProviderView,
    InstancesAnnotationRequest,
    InstancesAnnotationResponse,
    InteractiveAnnotationRequest,
    InteractiveAnnotationResponse,
)
from lightly_studio.services import assisted_labeling_service

annotate_router = APIRouter(prefix="/annotate", tags=["annotate"])

PROVIDER_MAX_WORKERS = 8


@annotate_router.get("/providers")
def list_assisted_labeling_providers() -> list[AssistedLabelingProviderView]:
    """Returns all providers."""
    return assisted_labeling_service.list_provider_views()


@annotate_router.post("/interactive")
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


@functools.cache
def _get_provider_executor() -> ThreadPoolExecutor:
    return ThreadPoolExecutor(
        max_workers=PROVIDER_MAX_WORKERS, thread_name_prefix="assisted_labeling"
    )


def _create_interactive_preview(
    request: InteractiveAnnotationRequest,
) -> InteractiveAnnotationResponse:
    provider, image = _resolve_provider_and_image(
        collection_id=request.collection_id, sample_id=request.sample_id
    )
    return assisted_labeling_service.create_interactive_preview(
        provider=provider, image=image, request=request
    )


def _create_instances_preview(
    request: InstancesAnnotationRequest,
) -> InstancesAnnotationResponse:
    provider, image = _resolve_provider_and_image(
        collection_id=request.collection_id, sample_id=request.sample_id
    )
    return assisted_labeling_service.create_instances_preview(
        provider=provider, image=image, request=request
    )


def _resolve_provider_and_image(
    collection_id: UUID, sample_id: UUID
) -> tuple[AssistedLabelingProvider, ProviderImage]:
    # No SessionDep: the session closes before the slow provider call.
    with db_manager.session() as session:
        provider = assisted_labeling_service.get_usable_provider(session=session)
        image = assisted_labeling_service.load_provider_image(
            session=session, collection_id=collection_id, sample_id=sample_id
        )
    return provider, image
