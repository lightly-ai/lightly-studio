"""Resolvers for caption."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import Session, col, func, select

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.caption import CaptionCreate, CaptionTable


class GetAllCaptionsResult(BaseModel):
    """Result wrapper for caption listings."""

    captions: Sequence[CaptionTable]
    total_count: int
    next_cursor: int | None = None


def create_many(session: Session, captions: Sequence[CaptionCreate]) -> list[CaptionTable]:
    """Create many captions in bulk.

    Args:
        session: Database session
        captions: The captions to create

    Returns:
        The created captions
    """
    if not captions:
        return []

    db_captions = [CaptionTable.model_validate(caption) for caption in captions]
    session.bulk_save_objects(db_captions)
    session.commit()
    return db_captions


def get_all(
    session: Session,
    dataset_id: UUID,
    pagination: Paginated | None = None,
) -> GetAllCaptionsResult:
    """Get all captions from the database.

    Args:
        session: Database session
        dataset_id: dataset_id parameter to filter the query
        pagination: Optional pagination parameters

    Returns:
        List of captions matching the filters, total number of captions, next cursor (pagination)
    """
    query = select(CaptionTable).order_by(
        col(CaptionTable.created_at).asc(),
        col(CaptionTable.caption_id).asc(),
    )
    count_query = select(func.count()).select_from(CaptionTable)

    query = query.where(CaptionTable.dataset_id == dataset_id)
    count_query = count_query.where(CaptionTable.dataset_id == dataset_id)

    if pagination is not None:
        query = query.offset(pagination.offset).limit(pagination.limit)

    captions = session.exec(query).all()
    total_count = session.exec(count_query).one()

    next_cursor: int | None = None
    if pagination and pagination.offset + pagination.limit < total_count:
        next_cursor = pagination.offset + pagination.limit

    return GetAllCaptionsResult(
        captions=captions,
        total_count=total_count,
        next_cursor=next_cursor,
    )
