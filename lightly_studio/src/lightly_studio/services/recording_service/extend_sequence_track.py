"""Set the extent of an object track on a sequence."""

from __future__ import annotations

import threading
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.annotation.annotation_base import AnnotationCreate, AnnotationType
from lightly_studio.models.annotation.cuboid_3d import Cuboid3DCreate
from lightly_studio.models.dataset import DatasetTable
from lightly_studio.models.mcap_sequence_tracks import SequenceTrackView, TrackAnnotationView
from lightly_studio.models.sequence import SampleSequenceLinkTable
from lightly_studio.resolvers import (
    annotation_resolver,
    collection_resolver,
    mcap_sequence_track_resolver,
    sample_resolver,
    sequence_resolver,
)
from lightly_studio.services.recording_service.get_ticks import get_ticks

# Serializes extent updates so a retry cannot add the same tick twice.
_EXTEND_LOCK = threading.Lock()


def extend_sequence_track(  # noqa: PLR0913
    session: Session,
    dataset_id: UUID,
    sequence_id: UUID,
    track_id: UUID,
    annotation_source_id: UUID,
    start_seq_number: int,
    end_seq_number: int,
) -> list[int] | None:
    """Set the track extent to `[start_seq_number, end_seq_number]`.

    Cuboids outside the requested range are deleted. Ticks before the first retained
    annotation or after the last retained annotation get a copy of that boundary cuboid.

    Args:
        session: The database session.
        dataset_id: The dataset the sequence must belong to.
        sequence_id: The sequence sample ID.
        track_id: The track to update.
        annotation_source_id: The annotation source holding the track's cuboids.
        start_seq_number: First tick the track should cover.
        end_seq_number: Last tick the track should cover.

    Returns:
        The tick numbers that received a new annotation, or `None` if the sequence does not
        exist or does not belong to `dataset_id`.

    Raises:
        ValueError: If the range is invalid, a tick is missing, or the track has no
            annotations from this source in the sequence.
    """
    tick_list = get_ticks(session=session, dataset_id=dataset_id, sequence_id=sequence_id)
    if tick_list is None:
        return None
    if start_seq_number > end_seq_number:
        raise ValueError("start_seq_number must not be greater than end_seq_number.")
    known = {tick.seq_number for tick in tick_list.ticks}
    if start_seq_number not in known or end_seq_number not in known:
        raise ValueError("The requested ticks do not exist in this sequence.")

    dataset_query = select(DatasetTable).where(col(DatasetTable.dataset_id) == dataset_id)
    if session.get_bind().dialect.name == "postgresql":
        dataset_query = dataset_query.with_for_update()
    dataset = session.exec(dataset_query).first()
    if dataset is None:
        return None

    with _EXTEND_LOCK:
        track = find_sequence_track(
            session=session,
            dataset_id=dataset_id,
            sequence_id=sequence_id,
            track_id=track_id,
            annotation_source_id=annotation_source_id,
        )
        by_seq = {annotation.seq_number: annotation for annotation in track.annotations}
        retained = {
            seq_number: annotation
            for seq_number, annotation in by_seq.items()
            if start_seq_number <= seq_number <= end_seq_number
        }
        if not retained:
            raise ValueError("The requested range must retain at least one track annotation.")
        removed = [
            annotation
            for annotation in track.annotations
            if not start_seq_number <= annotation.seq_number <= end_seq_number
        ]
        by_seq = retained
        first, last = min(by_seq), max(by_seq)
        targets = [
            (seq_number, first if seq_number < first else last)
            for seq_number in sorted(known)
            if start_seq_number <= seq_number <= end_seq_number
            and (seq_number < first or seq_number > last)
        ]
        created = (
            _create_copies(
                session=session,
                sequence_id=sequence_id,
                track=track,
                by_seq=by_seq,
                targets=targets,
                annotation_source_id=annotation_source_id,
            )
            if targets
            else []
        )
        if removed:
            annotation_resolver.delete_annotations_by_ids(
                session=session,
                annotation_ids=[annotation.annotation_id for annotation in removed],
            )
        return created


def find_sequence_track(
    session: Session,
    dataset_id: UUID,
    sequence_id: UUID,
    track_id: UUID,
    annotation_source_id: UUID,
) -> SequenceTrackView:
    """Return the track's annotations from one source of the sequence.

    Raises:
        ValueError: If the track has none.
    """
    tracks = mcap_sequence_track_resolver.get_all(
        session=session,
        dataset_id=dataset_id,
        sequence_id=sequence_id,
        annotation_source_id=annotation_source_id,
    )
    for track in tracks.tracks:
        if track.object_track_id == track_id:
            return track
    raise ValueError(f"Track {track_id} has no annotations from this source in the sequence.")


def _create_copies(  # noqa: PLR0913
    session: Session,
    sequence_id: UUID,
    track: SequenceTrackView,
    by_seq: dict[int, TrackAnnotationView],
    targets: list[tuple[int, int]],
    annotation_source_id: UUID,
) -> list[int]:
    links = {
        link.seq_number: link
        for link in sequence_resolver.get_sample_links(
            session=session, sequence_sample_id=sequence_id
        )
    }
    source = collection_resolver.get_by_id(session=session, collection_id=annotation_source_id)
    if source is None:
        raise ValueError(f"Annotation source {annotation_source_id} not found.")
    parent_collection_id = _parent_collection_id(
        session=session, first_tick_link=links[targets[0][0]]
    )

    boundary_cuboids: dict[int, Cuboid3DCreate] = {}
    label_id: UUID | None = None
    for boundary in {boundary for _, boundary in targets}:
        annotation = annotation_resolver.get_by_id(
            session=session, annotation_id=by_seq[boundary].annotation_id
        )
        if (
            annotation is None
            or annotation.annotation_type != AnnotationType.CUBOID_3D
            or annotation.cuboid_3d_details is None
        ):
            raise ValueError("The track's boundary annotation is not a cuboid.")
        details = annotation.cuboid_3d_details
        label_id = annotation.annotation_label_id
        boundary_cuboids[boundary] = Cuboid3DCreate(
            frame_id=details.frame_id,
            px=details.px,
            py=details.py,
            pz=details.pz,
            qx=details.qx,
            qy=details.qy,
            qz=details.qz,
            qw=details.qw,
            sx=details.sx,
            sy=details.sy,
            sz=details.sz,
            interpolated=True,
        )
    assert label_id is not None
    annotation_resolver.create_many(
        session=session,
        parent_collection_id=parent_collection_id,
        collection_name=source.name,
        annotations=[
            AnnotationCreate(
                parent_sample_id=links[seq_number].sample_id,
                annotation_label_id=label_id,
                annotation_type=AnnotationType.CUBOID_3D,
                object_track_id=track.object_track_id,
                cuboid_3d=boundary_cuboids[boundary],
            )
            for seq_number, boundary in targets
        ],
    )
    return [seq_number for seq_number, _ in targets]


def _parent_collection_id(session: Session, first_tick_link: SampleSequenceLinkTable) -> UUID:
    """Return the collection holding the tick samples that annotations attach to."""
    sample = sample_resolver.get_by_id(session=session, sample_id=first_tick_link.sample_id)
    if sample is None:
        raise ValueError("Tick sample not found.")
    return sample.collection_id
