"""API routes for dataset captions."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Path
from typing_extensions import Annotated

from lightly_studio.api.routes.api.status import HTTP_STATUS_NOT_FOUND
from lightly_studio.api.routes.api.validators import Paginated, PaginatedWithCursor
from lightly_studio.db_manager import SessionDep
from lightly_studio.models.caption import CaptionsListView, CaptionTable, CaptionView
from lightly_studio.resolvers import caption_resolver
from lightly_studio.resolvers.caption_resolver import GetAllCaptionsResult

captions_router = APIRouter(prefix="/datasets/{dataset_id}", tags=["captions"])


@captions_router.get("/captions", response_model=CaptionsListView)
def read_captions(
    dataset_id: Annotated[UUID, Path(title="Dataset Id")],
    session: SessionDep,
    pagination: Annotated[PaginatedWithCursor, Depends()],
) -> GetAllCaptionsResult:
    """Retrieve captions for a dataset."""
    return caption_resolver.get_all(
        session=session,
        dataset_id=dataset_id,
        pagination=Paginated(offset=pagination.offset, limit=pagination.limit),
    )


@captions_router.put("/captions/{caption_id}", response_model=CaptionView)
def update_caption_text(
    session: SessionDep,
    caption_id: Annotated[
        UUID,
        Path(title="Caption ID", description="ID of the caption to update"),
    ],
    text: Annotated[str, Body()],
) -> CaptionTable:
    """Update an existing caption in the database."""
    return caption_resolver.update_text(session=session, caption_id=caption_id, text=text)


@captions_router.get("/captions/{caption_id}", response_model=CaptionView)
def get_caption(
    session: SessionDep,
    caption_id: Annotated[UUID, Path(title="Caption ID")],
) -> CaptionTable:
    """Retrieve an existing annotation from the database."""
    captions = caption_resolver.get_by_ids(session, [caption_id])
    if not captions:
        raise ValueError(f"Caption with ID {caption_id} not found.")

    return captions[0]


@captions_router.delete("/captions/{caption_id}")
def delete_caption(
    session: SessionDep,
    caption_id: Annotated[
        UUID, Path(title="Caption ID", description="ID of the caption to delete")
    ],
) -> dict[str, str]:
    """Delete a caption from the database."""
    try:
        caption_resolver.delete_caption(session=session, caption_id=caption_id)
        return {"status": "deleted"}
    except ValueError as e:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail="Caption not found",
        ) from e
