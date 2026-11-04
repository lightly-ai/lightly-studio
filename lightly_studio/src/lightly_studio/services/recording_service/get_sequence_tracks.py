"""Sequence track read operations."""

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.mcap_sequence_tracks import SequenceTrackListView
from lightly_studio.resolvers import mcap_sequence_track_resolver
from lightly_studio.services.recording_service.get_ticks import get_ticks


def get_sequence_tracks(
    session: Session,
    dataset_id: UUID,
    sequence_id: UUID,
    annotation_source_id: UUID | None = None,
) -> SequenceTrackListView | None:
    """Return cuboid tracks for a sequence, or None if it is outside the dataset."""
    if get_ticks(session=session, dataset_id=dataset_id, sequence_id=sequence_id) is None:
        return None
    return mcap_sequence_track_resolver.get_all(
        session=session,
        dataset_id=dataset_id,
        sequence_id=sequence_id,
        annotation_source_id=annotation_source_id,
    )
