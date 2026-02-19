"""API routes for collection groups."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from lightly_studio.api.routes.api.validators import Paginated, PaginatedWithCursor
from lightly_studio.db_manager import SessionDep
from lightly_studio.models.group import GroupViewsWithCount
from lightly_studio.resolvers import group_resolver
from lightly_studio.resolvers.group_resolver.group_filter import GroupFilter

group_router = APIRouter(tags=["group"])


class ReadGroupsRequest(BaseModel):
    """Request body for reading groups."""

    filter: GroupFilter | None = Field(None, description="Filter parameters for groups")


@group_router.post("/groups", response_model=GroupViewsWithCount)
def get_all_groups(
    session: SessionDep,
    pagination: Annotated[PaginatedWithCursor, Depends()],
    body: ReadGroupsRequest,
) -> GroupViewsWithCount:
    """Retrieve a list of all groups with pagination.

    Args:
        session: The database session.
        pagination: Pagination parameters including offset and limit.
        body: The body containing filters, including collection_id in sample_filter.

    Returns:
        A list of groups along with the total count.
    """
    return group_resolver.get_all(
        session=session,
        pagination=Paginated(offset=pagination.offset, limit=pagination.limit),
        filters=body.filter,
    )
