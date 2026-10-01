"""API routes for MCAP sequences."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path

from lightly_studio.api.routes.api.validators import Paginated, PaginatedWithCursor
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.models.mcap_group_sequence import McapSequenceViewsWithCount
from lightly_studio.resolvers import mcap_group_sequence_resolver

mcap_sequence_router = APIRouter(tags=["mcap_sequence"])


@mcap_sequence_router.post(
    "/collections/{collection_id}/mcap-sequences/list",
    response_model=McapSequenceViewsWithCount,
)
def list_mcap_sequences(
    session: SessionDep,
    collection_id: Annotated[UUID, Path(title="Collection Id")],
    pagination: Annotated[PaginatedWithCursor, Depends()],
) -> McapSequenceViewsWithCount:
    """Retrieve a paginated list of MCAP sequences for a collection.

    Args:
        session: The database session.
        collection_id: The ID of the collection to fetch sequences for.
        pagination: Pagination parameters including offset (cursor) and limit.

    Returns:
        A paginated list of MCAP sequences with total count and next cursor.
    """
    return mcap_group_sequence_resolver.get_all_by_collection_id(
        session=session,
        collection_id=collection_id,
        pagination=Paginated(offset=pagination.offset, limit=pagination.limit),
    )
