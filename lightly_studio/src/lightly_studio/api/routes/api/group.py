"""API routes for collection groups."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Path
from pydantic import BaseModel, Field
from typing_extensions import Annotated

from lightly_studio.api.routes.api.validators import Paginated, PaginatedWithCursor
from lightly_studio.db_manager import SessionDep
from lightly_studio.models.group import GroupViewsWithCount
from lightly_studio.resolvers import group_resolver
from lightly_studio.resolvers.group_resolver.group_filter import GroupFilter

group_router = APIRouter(prefix="/collections/{collection_id}/group", tags=["group"])


class ReadGroupsRequest(BaseModel):
    """Request body for reading groups."""

    filter: Optional[GroupFilter] = Field(None, description="Filter parameters for groups")
    text_embedding: Optional[List[float]] = Field(None, description="Text embedding to search for")


@group_router.post("/", response_model=GroupViewsWithCount)
def get_all_groups(
    session: SessionDep,
    collection_id: Annotated[UUID, Path(title="collection Id")],
    pagination: Annotated[PaginatedWithCursor, Depends()],
    body: ReadGroupsRequest,
) -> GroupViewsWithCount:
    """Retrieve a list of all groups for a given collection ID with pagination.

    Args:
        session: The database session.
        collection_id: The ID of the collection to retrieve groups for.
        pagination: Pagination parameters including offset and limit.
        body: The body containing filters.

    Returns:
        A list of groups along with the total count.
    """
    return group_resolver.get_all_by_collection_id(
        session=session,
        collection_id=collection_id,
        pagination=Paginated(offset=pagination.offset, limit=pagination.limit),
        filters=body.filter,
        text_embedding=body.text_embedding,
    )
