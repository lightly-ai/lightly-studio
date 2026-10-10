"""API routes for AI-assisted labeling previews."""

from __future__ import annotations

from fastapi import APIRouter

from lightly_studio.api.routes.api.status import HTTP_STATUS_NO_CONTENT
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.models.assisted_labeling import (
    AssistedLabelingProviderView,
    InstancesAnnotationRequest,
    InstancesAnnotationResponse,
    InteractiveAnnotationRequest,
    InteractiveAnnotationResponse,
    PrepareAnnotationRequest,
)
from lightly_studio.services import assisted_labeling_service

annotate_router = APIRouter(prefix="/annotate", tags=["annotate"])


@annotate_router.get("/provider")
def get_assisted_labeling_provider(session: SessionDep) -> AssistedLabelingProviderView:
    """Returns the provider that the settings select."""
    return assisted_labeling_service.get_active_provider_view(session=session)


@annotate_router.get("/providers")
def list_assisted_labeling_providers() -> list[AssistedLabelingProviderView]:
    """Returns all providers."""
    return assisted_labeling_service.list_provider_views()


@annotate_router.post("/prepare", status_code=HTTP_STATUS_NO_CONTENT, response_model=None)
def prepare_annotation_image(session: SessionDep, request: PrepareAnnotationRequest) -> None:
    """Prepares an image for later preview requests, for example by uploading it."""
    assisted_labeling_service.prepare_image(session=session, request=request)


@annotate_router.post("/interactive")
def create_interactive_annotation_preview(
    session: SessionDep, request: InteractiveAnnotationRequest
) -> InteractiveAnnotationResponse:
    """Returns a single-object preview from points or boxes. Saves nothing."""
    return assisted_labeling_service.create_interactive_preview(session=session, request=request)


@annotate_router.post("/instances")
def create_instances_annotation_preview(
    session: SessionDep, request: InstancesAnnotationRequest
) -> InstancesAnnotationResponse:
    """Returns previews of all instances that match a text prompt or boxes. Saves nothing."""
    return assisted_labeling_service.create_instances_preview(session=session, request=request)
