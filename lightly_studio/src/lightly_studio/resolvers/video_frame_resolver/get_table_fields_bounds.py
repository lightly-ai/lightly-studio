"""Retrieve the minimum and maximum values of each video frame table field."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import Select, select
from sqlmodel import Session, col, func

from lightly_studio.models.range import IntRange
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.video import (
    VideoFrameFieldsBoundsView,
    VideoFrameTable,
)


def get_table_fields_bounds(
    session: Session,
    collection_id: UUID,
) -> VideoFrameFieldsBoundsView | None:
    """Find the minimum and maximum values (bounds) of the video frames fields.

    This includes frame number.
    """
    query: Select[tuple[Any, ...]] = (
        select(
            func.min(VideoFrameTable.frame_number).label("min_frame_number"),
            func.max(VideoFrameTable.frame_number).label("max_frame_number"),
        )
        .join(SampleTable)
        .where(col(SampleTable.collection_id) == collection_id)
    )

    result = session.execute(query).mappings().one()

    ## If the min_frame_number is empty, then no data is found.
    if result["min_frame_number"] is None:
        return None

    return VideoFrameFieldsBoundsView(
        frame_number=IntRange(min=result["min_frame_number"], max=result["max_frame_number"]),
    )
