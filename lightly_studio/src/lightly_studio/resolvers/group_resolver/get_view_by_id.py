"""Implementation of get_samples_excluding function for images."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.group import GroupView
from lightly_studio.models.sample import SampleView
from lightly_studio.resolvers import group_resolver


def get_view_by_id(session: Session, sample_id: UUID) -> GroupView:
    """Get the view for a given sample_id.

    Args:
        session: The database session.
        sample_id: The ID of the group to retrieve.

    Returns:
        The view for the given group.
    """
    group = group_resolver.get_by_id(session, sample_id)

    if group is None:
        raise ValueError(f"Group with sample_id '{sample_id}' not found.")

    group_collection_id = group_resolver.get_collection_id_by_group(
        session=session, sample_id=group.sample_id
    )
    if group_collection_id is None:
        raise ValueError(f"Collection not found for group with sample_id '{sample_id}'.")

    group_previews = group_resolver.get_group_previews(
        session=session,
        group_sample_ids=[group.sample_id],
        group_collection_id=group_collection_id,
    )
    group_sample_counts = group_resolver.get_group_sample_counts(
        session=session, group_sample_ids=[group.sample_id]
    )
    return GroupView(
        sample_id=group.sample_id,
        sample=SampleView.model_validate(group.sample),
        similarity_score=None,
        group_preview=group_previews.get(group.sample_id),
        sample_count=group_sample_counts.get(group.sample_id, 0),
    )
