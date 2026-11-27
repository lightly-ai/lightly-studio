"""Implementation of add_tag_to_sample function for tags."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers import tag_resolver


def add_tag_to_sample(
    session: Session,
    tag_id: UUID,
    sample: SampleTable,
) -> SampleTable | None:
    """Add a tag to a sample.

    Raises:
        ValueError: If the sample is not in the collection of the tag.
    """
    tag = tag_resolver.get_by_id(session=session, tag_id=tag_id)
    if not tag or not tag.tag_id:
        return None
    if sample.collection_id != tag.collection_id:
        raise ValueError(
            f"Sample {sample.sample_id} does not belong to the collection of tag '{tag.name}'."
        )

    sample.tags.append(tag)
    session.add(sample)
    session.commit()
    session.refresh(sample)
    return sample
