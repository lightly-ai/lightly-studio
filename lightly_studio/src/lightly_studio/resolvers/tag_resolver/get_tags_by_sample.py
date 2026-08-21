"""Implementation of get_tags_by_sample function for tags."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.database import db_array
from lightly_studio.models.sample import SampleTagLinkTable


def get_tags_by_sample(
    session: Session,
    tag_ids: Sequence[UUID],
) -> dict[UUID, set[UUID]]:
    """Return ``{sample_id: {tag_id, ...}}`` for the requested tags."""
    if not tag_ids:
        return {}
    stmt = select(SampleTagLinkTable.sample_id, SampleTagLinkTable.tag_id).where(
        db_array.in_array(column=col(SampleTagLinkTable.tag_id), values=tag_ids)
    )
    result: dict[UUID, set[UUID]] = {}
    for sample_id, tag_id in session.exec(stmt).all():
        assert sample_id is not None
        assert tag_id is not None
        result.setdefault(sample_id, set()).add(tag_id)
    return result
