"""Service function for the tags on the ticks of an MCAP sequence."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.mcap_sequence_ticks import TickTagListView, TickTagView
from lightly_studio.resolvers import sequence_resolver
from lightly_studio.services.recording_service.get_ticks import get_ticks


def get_tick_tags(
    session: Session,
    dataset_id: UUID,
    sequence_id: UUID,
) -> TickTagListView | None:
    """Return the tags on the ticks of an MCAP sequence, grouped by tag.

    Args:
        session: The database session.
        dataset_id: The dataset the sequence must belong to.
        sequence_id: The sequence sample ID.

    Returns:
        One entry per tag that is on at least one tick, ordered by tag name, or `None`
        if the sequence does not exist or does not belong to `dataset_id`.
    """
    if get_ticks(session=session, dataset_id=dataset_id, sequence_id=sequence_id) is None:
        return None
    tags_by_id: dict[UUID, TickTagView] = {}
    for tag, seq_number in sequence_resolver.get_tag_links(
        session=session, sequence_sample_id=sequence_id
    ):
        tag_view = tags_by_id.setdefault(
            tag.tag_id, TickTagView(tag_id=tag.tag_id, name=tag.name, seq_numbers=[])
        )
        tag_view.seq_numbers.append(seq_number)
    return TickTagListView(tags=list(tags_by_id.values()))
