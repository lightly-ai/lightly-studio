"""Read tag memberships without constructing UUID objects for every link."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from uuid import UUID

from sqlalchemy import String, cast
from sqlmodel import Session, col, select

from lightly_studio.database import db_array
from lightly_studio.models.sample import SampleTable, SampleTagLinkTable


def iter_sample_memberships(
    session: Session, tag_ids: Sequence[UUID], collection_id: UUID | None = None
) -> Iterator[tuple[str, str]]:
    """Yield unique (sample ID, tag ID) string pairs for the requested tags.

    Cast only the selected columns to avoid decoding two UUIDs per membership;
    the predicate retains the indexed UUID column. The link's composite primary
    key guarantees unique pairs, even when requested tag IDs repeat.

    Args:
        session: Database session, which must stay open during iteration.
        tag_ids: Tags whose memberships to read.
        collection_id: If given, include only samples from this collection.

    Yields:
        Sample and tag IDs as canonical UUID strings.
    """
    if not tag_ids:
        return
    stmt = select(
        cast(col(SampleTagLinkTable.sample_id), String),
        cast(col(SampleTagLinkTable.tag_id), String),
    ).where(db_array.in_array(column=col(SampleTagLinkTable.tag_id), values=tag_ids))
    if collection_id is not None:
        stmt = stmt.join(
            SampleTable, col(SampleTable.sample_id) == col(SampleTagLinkTable.sample_id)
        ).where(SampleTable.collection_id == collection_id)
    yield from session.exec(stmt)
