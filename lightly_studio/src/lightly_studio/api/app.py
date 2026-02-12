"""This module contains the FastAPI app configuration."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Awaitable
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import APIRouter, Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from sqlmodel import Session
from typing_extensions import Annotated

from lightly_studio import db_manager
from lightly_studio.api import server_timing
from lightly_studio.api.routes import (
    healthz,
    images,
    video_frames_media,
    video_media,
    webapp,
)
from lightly_studio.api.routes.api import (
    annotation,
    annotation_label,
    caption,
    classifier,
    collection,
    collection_tag,
    embeddings2d,
    export,
    features,
    frame,
    group,
    image,
    image_embedding,
    metadata,
    operator,
    sample,
    selection,
    settings,
    text_embedding,
    video,
)
from lightly_studio.api.routes.api.exceptions import (
    register_exception_handlers,
)
from lightly_studio.dataset.env import (
    LIGHTLY_STUDIO_DEBUG,
    LIGHTLY_STUDIO_SERVER_TIMING_ENABLED,
)

SessionDep = Annotated[Session, Depends(db_manager.session)]


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context for initializing and cleaning up resources.

    Args:
        _: The FastAPI application instance.

    Yields:
        None when the application is ready.
    """
    try:
        yield
    finally:  # we need an explicit close for the db manager to make a final write to disk
        db_manager.close()


if LIGHTLY_STUDIO_DEBUG:
    import logging

    # TODO(Lukas, 12/2025): move this into setup_logging.py, drop `basicConfig()`. Also everything
    # seems to be on the INFO level. `logging.DEBUG` maybe doesn't make a difference.
    logging.basicConfig()
    logger = logging.getLogger("sqlalchemy.engine")
    logger.setLevel(logging.DEBUG)

"""Create the FastAPI app."""
app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Server-Timing"],
)


@app.middleware("http")
async def add_server_timing_header(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Add backend and database timing metrics to the response headers."""
    if not LIGHTLY_STUDIO_SERVER_TIMING_ENABLED:
        return await call_next(request)

    request_start_time, token = server_timing.start_request_timing()

    try:
        response = await call_next(request)
    except Exception:
        server_timing.finish_request_timing(request_start_time=request_start_time, token=token)
        raise

    total_ms, db_ms, backend_ms = server_timing.finish_request_timing(
        request_start_time=request_start_time,
        token=token,
    )
    response.headers["Server-Timing"] = server_timing.format_server_timing_header(
        total_ms=total_ms,
        db_ms=db_ms,
        backend_ms=backend_ms,
    )
    return response


def use_route_names_as_operation_ids(app: FastAPI) -> None:
    """Use API function name for operation IDs.

    Should be called only after all routes have been added.
    """
    for route in app.routes:
        if isinstance(route, APIRoute):
            route.operation_id = route.name  # in this case, 'read_items'


register_exception_handlers(app)

# api routes
api_router = APIRouter(prefix="/api", tags=["api"])

api_router.include_router(collection.collection_router)
api_router.include_router(collection_tag.tag_router)
api_router.include_router(export.export_router)
api_router.include_router(image.image_router)
api_router.include_router(sample.sample_router)
api_router.include_router(annotation_label.annotations_label_router)
api_router.include_router(annotation.annotations_router)
api_router.include_router(caption.captions_router)
api_router.include_router(text_embedding.text_embedding_router)
api_router.include_router(image_embedding.image_embedding_router)
api_router.include_router(settings.settings_router)
api_router.include_router(classifier.classifier_router)
api_router.include_router(embeddings2d.embeddings2d_router)
api_router.include_router(features.features_router)
api_router.include_router(metadata.metadata_router)
api_router.include_router(selection.selection_router)
api_router.include_router(operator.operator_router)
api_router.include_router(frame.frame_router)
api_router.include_router(video.video_router)
api_router.include_router(group.group_router)

app.include_router(api_router)

# images serving
app.include_router(images.app_router, prefix="/images")
app.include_router(video_frames_media.frames_router)
app.include_router(video_media.app_router)

# health status check
app.include_router(healthz.health_router)

# webapp routes
app.include_router(webapp.app_router)

use_route_names_as_operation_ids(app)
