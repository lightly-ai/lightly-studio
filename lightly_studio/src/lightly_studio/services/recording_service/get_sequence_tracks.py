"""Sequence track read operations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from uuid import UUID

from sqlmodel import Session

from lightly_studio.core.mcap.errors import McapAccessError
from lightly_studio.core.mcap.reader import McapFileReader, calibration
from lightly_studio.core.mcap.type_definitions import StaticTransform
from lightly_studio.models.mcap_sequence_tracks import SequenceTrackListView
from lightly_studio.resolvers import (
    mcap_group_sequence_resolver,
    mcap_sequence_track_resolver,
    recording_resolver,
)
from lightly_studio.services.recording_service import (
    load_dynamic_transforms,
    load_static_transforms,
    reader_cache,
    transform_to_target_frame,
)
from lightly_studio.services.recording_service.get_ticks import get_ticks
from lightly_studio.services.recording_service.load_dynamic_transforms import (
    DynamicTransformsByTime,
)


def get_sequence_tracks(
    session: Session,
    dataset_id: UUID,
    sequence_id: UUID,
    annotation_source_id: UUID | None = None,
    target_frame_id: str | None = None,
) -> SequenceTrackListView | None:
    """Return cuboid tracks for a sequence, or None if it is outside the dataset.

    Args:
        session: The database session.
        dataset_id: The dataset the sequence must belong to.
        sequence_id: The sequence sample ID.
        annotation_source_id: Only return annotations from this annotation source.
        target_frame_id: The coordinate frame the scene is shown in. A tick's
            annotations are left out if its cuboids cannot be mapped to this frame,
            because the scene cannot show them there either. `None` keeps every
            annotation.

    Returns:
        The tracks with their annotations, or `None` if the sequence does not exist
        or does not belong to `dataset_id`.
    """
    tick_list = get_ticks(session=session, dataset_id=dataset_id, sequence_id=sequence_id)
    if tick_list is None:
        return None
    tracks = mcap_sequence_track_resolver.get_all(
        session=session,
        dataset_id=dataset_id,
        sequence_id=sequence_id,
        annotation_source_id=annotation_source_id,
    )
    if target_frame_id is None:
        return tracks

    frame_ids_by_seq_number: dict[int, set[str]] = {}
    for track in tracks.tracks:
        for annotation in track.annotations:
            frame_ids_by_seq_number.setdefault(annotation.seq_number, set()).add(
                annotation.frame_id
            )
    hidden_seq_numbers = _seq_numbers_outside_frame(
        session=session,
        sequence_id=sequence_id,
        timestamps_ns={tick.seq_number: tick.timestamp_ns for tick in tick_list.ticks},
        frame_ids_by_seq_number=frame_ids_by_seq_number,
        target_frame_id=target_frame_id,
    )
    if not hidden_seq_numbers:
        return tracks
    for track in tracks.tracks:
        track.annotations = [
            annotation
            for annotation in track.annotations
            if annotation.seq_number not in hidden_seq_numbers
        ]
    return tracks


def _seq_numbers_outside_frame(
    session: Session,
    sequence_id: UUID,
    timestamps_ns: Mapping[int, int | None],
    frame_ids_by_seq_number: Mapping[int, set[str]],
    target_frame_id: str,
) -> set[int]:
    """Return the ticks whose cuboids cannot be mapped to the target frame.

    This matches the tick details: a tick whose cuboids cannot all be mapped shows
    none of them. The transforms are loaded once for all ticks.
    """
    source_frame_ids_by_seq_number = {
        seq_number: frame_ids - {target_frame_id}
        for seq_number, frame_ids in frame_ids_by_seq_number.items()
        if frame_ids - {target_frame_id}
    }
    if not source_frame_ids_by_seq_number:
        return set()

    hidden = {
        seq_number
        for seq_number in source_frame_ids_by_seq_number
        if timestamps_ns.get(seq_number) is None
    }
    timed = {
        seq_number: timestamp_ns
        for seq_number in source_frame_ids_by_seq_number
        if (timestamp_ns := timestamps_ns.get(seq_number)) is not None
    }
    if not timed:
        return hidden

    sequence = mcap_group_sequence_resolver.get_by_id(session=session, sample_id=sequence_id)
    recording = (
        None
        if sequence is None
        else recording_resolver.get_by_id(session=session, recording_id=sequence.recording_id)
    )
    if recording is None:
        return hidden | set(timed)

    static_transforms = load_static_transforms.load_static_transforms(
        session=session, recording_id=recording.recording_id
    )
    window_ns = calibration.DYNAMIC_TRANSFORM_WINDOW_NS
    dynamic_edges = load_dynamic_transforms.load_dynamic_transforms_between(
        session=session,
        recording_id=recording.recording_id,
        start_ns=max(min(timed.values()) - window_ns, 0),
        end_ns=max(timed.values()) + window_ns,
    )
    dynamic_transforms = None if dynamic_edges is None else DynamicTransformsByTime(dynamic_edges)
    with reader_cache.borrow_reader(uri=recording.uri) as reader:
        for seq_number, timestamp_ns in timed.items():
            if not _can_map_frames(
                reader=reader,
                source_frame_ids=source_frame_ids_by_seq_number[seq_number],
                target_frame_id=target_frame_id,
                timestamp_ns=timestamp_ns,
                static_transforms=static_transforms,
                dynamic_transforms=None
                if dynamic_transforms is None
                else dynamic_transforms.near(timestamp_ns=timestamp_ns),
            ):
                hidden.add(seq_number)
    return hidden


def _can_map_frames(  # noqa: PLR0913
    reader: McapFileReader,
    source_frame_ids: set[str],
    target_frame_id: str,
    timestamp_ns: int,
    static_transforms: Sequence[StaticTransform],
    dynamic_transforms: Sequence[StaticTransform] | None,
) -> bool:
    """Whether a chain of transforms connects every source frame to the target."""
    try:
        for source_frame_id in source_frame_ids:
            transform_to_target_frame.transform_to_target_frame(
                reader=reader,
                source_frame_id=source_frame_id,
                target_frame_id=target_frame_id,
                timestamp_ns=timestamp_ns,
                static_transforms=static_transforms,
                dynamic_transforms=dynamic_transforms,
            )
    except McapAccessError:
        return False
    return True
