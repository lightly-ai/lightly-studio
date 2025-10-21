"""API routes for dataset captions."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Path
from typing_extensions import Annotated

from lightly_studio.api.routes.api.validators import Paginated, PaginatedWithCursor
from lightly_studio.db_manager import SessionDep
from lightly_studio.models.caption import CaptionsListView
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
