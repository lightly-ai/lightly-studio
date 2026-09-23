"""Implementation of remove_tag_from_sample function for tags."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers import tag_resolver


def remove_tag_from_sample(
    session: Session,
    tag_id: UUID,
    sample: SampleTable,
) -> SampleTable | None:
    """Remove a tag from a sample."""
    tag = tag_resolver.get_by_id(session=session, tag_id=tag_id)
    if not tag or not tag.tag_id:
        return None

    sample.tags.remove(tag)
    session.add(sample)
    session.commit()
    session.refresh(sample)
    return sample
