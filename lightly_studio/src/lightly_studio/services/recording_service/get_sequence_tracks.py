"""Read-only tracked cuboids for an MCAP sequence."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation.cuboid_3d import Cuboid3DAnnotationTable
from lightly_studio.models.annotation.object_track import ObjectTrackTable
from lightly_studio.models.mcap_sequence_tracks import (
    SequenceTrackListView,
    SequenceTrackView,
    TrackAnnotationView,
)
from lightly_studio.models.sequence import SampleSequenceLinkTable
from lightly_studio.services.recording_service.get_ticks import get_ticks


def get_sequence_tracks(
    session: Session, dataset_id: UUID, sequence_id: UUID
) -> SequenceTrackListView | None:
    """Return tracked cuboids at ticks in the requested MCAP sequence.

    Returns None if the sequence does not belong to the dataset. The query joins through
    sequence links, so a dataset-scoped track cannot leak annotations from another sequence.
    """
    if get_ticks(session=session, dataset_id=dataset_id, sequence_id=sequence_id) is None:
        return None

    statement = (
        select(
            ObjectTrackTable,
            SampleSequenceLinkTable.seq_number,
            AnnotationBaseTable.sample_id,
            Cuboid3DAnnotationTable.interpolated,
        )
        .join(
            AnnotationBaseTable,
            col(AnnotationBaseTable.object_track_id) == col(ObjectTrackTable.object_track_id),
        )
        .join(
            SampleSequenceLinkTable,
            col(SampleSequenceLinkTable.sample_id) == col(AnnotationBaseTable.parent_sample_id),
        )
        .join(
            Cuboid3DAnnotationTable,
            col(Cuboid3DAnnotationTable.sample_id) == col(AnnotationBaseTable.sample_id),
        )
        .where(
            col(SampleSequenceLinkTable.sequence_sample_id) == sequence_id,
            col(ObjectTrackTable.dataset_id) == dataset_id,
        )
        .order_by(
            col(ObjectTrackTable.object_track_number),
            col(ObjectTrackTable.object_track_id),
            col(SampleSequenceLinkTable.seq_number),
            col(AnnotationBaseTable.sample_id),
        )
    )
    tracks: dict[UUID, SequenceTrackView] = {}
    for track_row, seq_number, annotation_id, interpolated in session.exec(statement):
        track_id = track_row.object_track_id
        track = tracks.setdefault(
            track_id,
            SequenceTrackView(
                object_track_id=track_id,
                object_track_number=track_row.object_track_number,
                annotations=[],
            ),
        )
        track.annotations.append(
            TrackAnnotationView(
                seq_number=seq_number,
                annotation_id=annotation_id,
                interpolated=interpolated,
            )
        )
    return SequenceTrackListView(tracks=list(tracks.values()))
