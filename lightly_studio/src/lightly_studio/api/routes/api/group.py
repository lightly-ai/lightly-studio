"""API routes for collection groups."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path
from pydantic import BaseModel, Field

from lightly_studio.api.routes.api.validators import Paginated, PaginatedWithCursor
from lightly_studio.db_manager import SessionDep
from lightly_studio.models.group import GroupComponentView, GroupViewsWithCount
from lightly_studio.resolvers import group_resolver
from lightly_studio.resolvers.group_resolver.group_filter import GroupFilter

group_router = APIRouter(tags=["group"])


class ReadGroupsRequest(BaseModel):
    """Request body for reading groups."""

    filter: GroupFilter | None = Field(None, description="Filter parameters for groups")


@group_router.post("/collections/{collection_id}/groups", response_model=GroupViewsWithCount)
def get_all_groups(
    session: SessionDep,
    collection_id: Annotated[UUID, Path(title="Collection Id")],
    pagination: Annotated[PaginatedWithCursor, Depends()],
    body: ReadGroupsRequest,
) -> GroupViewsWithCount:
    """Retrieve a list of all groups with pagination.

    Args:
        session: The database session.
        collection_id: The ID of the collection to fetch groups for.
        pagination: Pagination parameters including offset and limit.
        body: The body containing filters.

    Returns:
        A list of groups along with the total count.
    """
    return group_resolver.get_all(
        session=session,
        collection_id=collection_id,
        pagination=Paginated(offset=pagination.offset, limit=pagination.limit),
        filters=body.filter,
    )


@group_router.get("/groups/{group_id}/components", response_model=list[GroupComponentView])
def get_group_components_by_group_id(
    session: SessionDep,
    group_id: Annotated[UUID, Path(title="Group Id")],
) -> list[GroupComponentView]:
    """Get all component views that belong to a group sample."""
    # Extract groupcomponent details for each sample
    return group_resolver.get_group_component_details_by_group_id(
        session=session, group_id=group_id
    )
