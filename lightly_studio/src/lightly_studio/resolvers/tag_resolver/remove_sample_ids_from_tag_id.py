"""Implementation of remove_sample_ids_from_tag_id function for tags."""

from __future__ import annotations

from uuid import UUID

import sqlmodel
from sqlmodel import Session, col

from lightly_studio.models.sample import SampleTagLinkTable
from lightly_studio.models.tag import TagTable
from lightly_studio.resolvers import tag_resolver
from lightly_studio.utils import batching


def remove_sample_ids_from_tag_id(
    session: Session,
    tag_id: UUID,
    sample_ids: list[UUID],
) -> TagTable | None:
    """Remove a list of sample_ids from a tag."""
    tag = tag_resolver.get_by_id(session=session, tag_id=tag_id)
    if not tag or not tag.tag_id:
        return None

    for batch in batching.batched(items=sample_ids):
        session.exec(
            sqlmodel.delete(SampleTagLinkTable).where(
                col(SampleTagLinkTable.tag_id) == tag_id,
                col(SampleTagLinkTable.sample_id).in_(batch),
            )
        )

    session.commit()
    session.refresh(tag)
    return tag
