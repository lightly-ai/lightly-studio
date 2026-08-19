"""Fetch and validate sample tags for a collection."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.database import db_array
from lightly_studio.models.tag import TagTable


def get_and_validate_sample_tags(
    session: Session,
    collection_id: UUID,
    sample_tag_ids: list[UUID],
) -> dict[UUID, str]:
    """Return {tag_id: name} for the given IDs, raising if any are invalid."""
    query = select(TagTable.tag_id, TagTable.name).where(
        col(TagTable.collection_id) == collection_id,
        col(TagTable.kind) == "sample",
        db_array.in_array(column=col(TagTable.tag_id), values=sample_tag_ids),
    )
    sample_tags = dict(session.exec(query).all())
    invalid_ids = set(sample_tag_ids) - sample_tags.keys()
    if invalid_ids:
        ids = ", ".join(sorted(str(tag_id) for tag_id in invalid_ids))
        raise ValueError(
            f"Tags must be sample tags belonging to collection {collection_id}: {ids}."
        )
    return sample_tags
