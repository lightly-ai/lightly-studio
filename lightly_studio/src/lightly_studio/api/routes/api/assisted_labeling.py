"""API routes for assisted labeling."""

from __future__ import annotations

import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header

from lightly_studio.assisted_labeling import (
    fal_sam3_provider,
    labeling_model_lookup,
    remote_runner_cache,
)
from lightly_studio.assisted_labeling.provider import ProviderImage
from lightly_studio.assisted_labeling.remote_runner_cache import RemoteLabelingModelConfig
from lightly_studio.database import db_manager
from lightly_studio.errors import NotFoundError
from lightly_studio.models.assisted_labeling import (
    AssistedLabelingStatusView,
    InstancesAnnotationRequest,
    InstancesAnnotationResponse,
    InteractiveAnnotationRequest,
    InteractiveAnnotationResponse,
    LabelingModelsView,
    LabelingModelView,
    ModelAnnotationRequest,
    ModelAnnotationResponse,
)
from lightly_studio.resolvers import collection_resolver, labeling_model_resolver
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
    x_user_email: Annotated[str | None, Header()] = None,
) -> InteractiveAnnotationResponse:
    """Returns a single-object preview from points or boxes. Saves nothing.

    `X-User-Email` is set by the auth proxy of a hosted deployment and attributes the
    usage to the user.
    """
    return await asyncio.get_running_loop().run_in_executor(
        _get_provider_executor(),
        functools.partial(
            _create_interactive_preview,
            request=request,
            user_email=_to_user_email(x_user_email=x_user_email),
        ),
    )


@assisted_labeling_router.post("/instances")
async def create_instances_annotation_preview(
    request: InstancesAnnotationRequest,
    x_user_email: Annotated[str | None, Header()] = None,
) -> InstancesAnnotationResponse:
    """Returns previews of all instances that match a text prompt. Saves nothing.

    `X-User-Email` is set by the auth proxy of a hosted deployment and attributes the
    usage to the user.
    """
    return await asyncio.get_running_loop().run_in_executor(
        _get_provider_executor(),
        functools.partial(
            _create_instances_preview,
            request=request,
            user_email=_to_user_email(x_user_email=x_user_email),
        ),
    )


@assisted_labeling_router.get("/models")
def get_labeling_models(collection_id: UUID) -> LabelingModelsView:
    """Returns the labeling models that the GUI can run on the images of the collection."""
    saved_models = _load_saved_models(collection_id=collection_id)
    return LabelingModelsView(
        models=[
            LabelingModelView(id=runner.model_id, task=runner.task, class_names=runner.class_names)
            for runner in labeling_model_lookup.list_runners(saved_models=saved_models)
        ]
    )


@assisted_labeling_router.post("/model")
async def create_model_annotation_preview(
    request: ModelAnnotationRequest,
) -> ModelAnnotationResponse:
    """Returns previews of the annotations that a labeling model predicts. Saves nothing."""
    return await asyncio.get_running_loop().run_in_executor(
        _get_provider_executor(), functools.partial(_create_model_preview, request=request)
    )


def _get_provider_executor() -> ThreadPoolExecutor:
    return executor.get_media_executor(
        thread_name_prefix="assisted_labeling", max_workers=PROVIDER_MAX_WORKERS
    )


def _create_interactive_preview(
    request: InteractiveAnnotationRequest, user_email: str | None
) -> InteractiveAnnotationResponse:
    image = _load_image(collection_id=request.collection_id, sample_id=request.sample_id)
    return assisted_labeling_service.create_interactive_preview(
        provider=fal_sam3_provider.get_provider(),
        image=image,
        request=request,
        user_email=user_email,
    )


def _create_instances_preview(
    request: InstancesAnnotationRequest, user_email: str | None
) -> InstancesAnnotationResponse:
    image = _load_image(collection_id=request.collection_id, sample_id=request.sample_id)
    return assisted_labeling_service.create_instances_preview(
        provider=fal_sam3_provider.get_provider(),
        image=image,
        request=request,
        user_email=user_email,
    )


def _create_model_preview(request: ModelAnnotationRequest) -> ModelAnnotationResponse:
    runner = labeling_model_lookup.get_runner(
        model_id=request.model_id,
        saved_models=_load_saved_models(collection_id=request.collection_id),
    )
    image = _load_image(collection_id=request.collection_id, sample_id=request.sample_id)
    return assisted_labeling_service.create_model_preview(
        runner=runner, image=image, request=request
    )


def _load_saved_models(collection_id: UUID) -> list[RemoteLabelingModelConfig]:
    """Returns the labeling servers that the dataset of the collection saves.

    Raises:
        NotFoundError: If the collection does not exist.
    """
    # No SessionDep: the session closes before a slow connection to a server.
    with db_manager.session() as session:
        collection = collection_resolver.get_by_id(session=session, collection_id=collection_id)
        if collection is None:
            raise NotFoundError(f"Collection {collection_id} not found.")
        saved_models = labeling_model_resolver.get_all_by_dataset_id(
            session=session, dataset_id=collection.dataset_id
        )
        return [
            remote_runner_cache.from_labeling_model(labeling_model=labeling_model)
            for labeling_model in saved_models
        ]


def _load_image(collection_id: UUID, sample_id: UUID) -> ProviderImage:
    # No SessionDep: the session closes before the slow provider call.
    with db_manager.session() as session:
        return assisted_labeling_service.load_provider_image(
            session=session, collection_id=collection_id, sample_id=sample_id
        )


def _to_user_email(x_user_email: str | None) -> str | None:
    """Returns the forwarded user email, or None if the header is missing or blank."""
    if x_user_email is None:
        return None
    return x_user_email.strip() or None
