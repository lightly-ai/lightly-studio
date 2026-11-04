"""Read tracked cuboids for an MCAP sequence."""

from uuid import UUID

from sqlalchemy import select
from sqlmodel import Session, col

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation.cuboid_3d import Cuboid3DAnnotationTable
from lightly_studio.models.annotation.object_track import ObjectTrackTable
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.mcap_sequence_tracks import (
    SequenceTrackListView,
    SequenceTrackView,
    TrackAnnotationView,
)
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.sequence import SampleSequenceLinkTable


def get_all(
    session: Session,
    dataset_id: UUID,
    sequence_id: UUID,
    annotation_source_id: UUID | None = None,
) -> SequenceTrackListView:
    """Return tracked cuboids in a sequence, optionally limited to one source."""
    statement = (
        select(
            ObjectTrackTable,
            col(SampleSequenceLinkTable.seq_number),
            col(AnnotationBaseTable.sample_id),
            col(SampleTable.collection_id),
            col(Cuboid3DAnnotationTable.frame_id),
            col(Cuboid3DAnnotationTable.interpolated),
            col(AnnotationLabelTable.annotation_label_name),
            col(CollectionTable.name),
        )
        .join(
            AnnotationBaseTable,
            col(AnnotationBaseTable.object_track_id) == col(ObjectTrackTable.object_track_id),
        )
        .join(
            SampleSequenceLinkTable,
            col(SampleSequenceLinkTable.sample_id) == col(AnnotationBaseTable.parent_sample_id),
        )
        .join(SampleTable, col(SampleTable.sample_id) == col(AnnotationBaseTable.sample_id))
        .join(CollectionTable, col(CollectionTable.collection_id) == col(SampleTable.collection_id))
        .join(
            Cuboid3DAnnotationTable,
            col(Cuboid3DAnnotationTable.sample_id) == col(AnnotationBaseTable.sample_id),
        )
        .join(
            AnnotationLabelTable,
            col(AnnotationLabelTable.annotation_label_id)
            == col(AnnotationBaseTable.annotation_label_id),
        )
        .where(
            col(SampleSequenceLinkTable.sequence_sample_id) == sequence_id,
            col(ObjectTrackTable.dataset_id) == dataset_id,
        )
        .order_by(
            col(ObjectTrackTable.object_track_number),
            col(ObjectTrackTable.object_track_id),
            col(SampleSequenceLinkTable.seq_number),
        )
    )
    if annotation_source_id is not None:
        statement = statement.where(col(SampleTable.collection_id) == annotation_source_id)

    tracks: dict[tuple[UUID, UUID], SequenceTrackView] = {}
    for (
        track,
        seq_number,
        annotation_id,
        source_id,
        frame_id,
        interpolated,
        label_name,
        source_name,
    ) in session.execute(statement):
        key = (track.object_track_id, source_id)
        if key not in tracks:
            tracks[key] = SequenceTrackView(
                object_track_id=track.object_track_id,
                object_track_number=track.object_track_number,
                annotation_source_id=source_id,
                annotation_source_name=source_name,
                annotation_label_name=label_name,
                annotations=[],
            )
        tracks[key].annotations.append(
            TrackAnnotationView(
                seq_number=seq_number,
                annotation_id=annotation_id,
                annotation_source_id=source_id,
                frame_id=frame_id,
                interpolated=interpolated,
            )
        )
    return SequenceTrackListView(tracks=list(tracks.values()))
