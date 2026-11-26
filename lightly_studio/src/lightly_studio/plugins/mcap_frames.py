"""Read the frames of MCAP sequences in a plugin, without decoding sensor data."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationView
from lightly_studio.models.collection import SampleType
from lightly_studio.models.recording import RecordingTable
from lightly_studio.models.sequence import SampleSequenceLinkTable
from lightly_studio.plugins.operator_context import ExecutionContext
from lightly_studio.resolvers import (
    annotation_resolver,
    collection_resolver,
    mcap_group_sequence_resolver,
    mcap_resolver,
    recording_resolver,
    sequence_resolver,
    tag_resolver,
)
from lightly_studio.resolvers.annotation_resolver import parent_track_lookup
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.utils import batching

_FRAME_CHUNK_SIZE = 100


@dataclass(frozen=True)
class McapFrame:
    """One frame (tick) of an MCAP sequence.

    Attributes:
        sample_id: The sample ID of the tick group.
        timestamp_ns: The capture time of the sync component.
        capture_timestamps_ns: The capture time of each component, keyed by its name.
        annotations: The annotations of all annotation sets. Cuboids stay in their own
            coordinate frame.
    """

    sequence_id: UUID
    seq_number: int
    sample_id: UUID
    recording_id: UUID
    recording_uri: str
    timestamp_ns: int | None
    capture_timestamps_ns: dict[str, int]
    annotations: list[AnnotationView]
    tags: list[str]


def get_sequence_ids(session: Session, context: ExecutionContext) -> list[UUID]:
    """Returns the sorted IDs of the MCAP sequences in the context.

    Raises:
        ValueError: If the context collection is not an MCAP sequence collection.
    """
    collection = collection_resolver.get_by_id(session=session, collection_id=context.collection_id)
    if collection is None or collection.sample_type != SampleType.SEQUENCE:
        raise ValueError("MCAP frames can only be read from an MCAP sequence collection.")
    sequence_ids = mcap_group_sequence_resolver.get_sample_ids(
        session=session, collection_id=collection.collection_id
    )
    context_filter = context.context_filter
    if isinstance(context_filter, SampleFilter) and context_filter.sample_ids is not None:
        sequence_ids &= set(context_filter.sample_ids)
    return sorted(sequence_ids)


def iter_frames(session: Session, sequence_ids: Sequence[UUID]) -> Iterator[McapFrame]:
    """Returns the frames of the sequences in order. The session must stay open.

    Raises:
        ValueError: If a sequence is not an MCAP sequence.
    """
    recordings = [
        _recording(session=session, sequence_id=sequence_id) for sequence_id in sequence_ids
    ]
    return _frames(session=session, sequence_ids=sequence_ids, recordings=recordings)


def _frames(
    session: Session, sequence_ids: Sequence[UUID], recordings: Sequence[RecordingTable]
) -> Iterator[McapFrame]:
    """Yields the frames of each sequence."""
    for sequence_id, recording in zip(sequence_ids, recordings):
        links = sequence_resolver.get_sample_links(session=session, sequence_sample_id=sequence_id)
        for chunk in batching.batched(items=links, batch_size=_FRAME_CHUNK_SIZE):
            yield from _chunk_frames(session=session, links=chunk, recording=recording)


def _chunk_frames(
    session: Session, links: Sequence[SampleSequenceLinkTable], recording: RecordingTable
) -> list[McapFrame]:
    """Reads the frames of a chunk of links."""
    group_sample_ids = [link.sample_id for link in links]
    annotations = _annotations_by_group(session=session, group_sample_ids=group_sample_ids)
    tags = tag_resolver.get_names_by_sample_ids(session=session, sample_ids=group_sample_ids)
    return [
        McapFrame(
            sequence_id=link.sequence_sample_id,
            seq_number=link.seq_number,
            sample_id=link.sample_id,
            recording_id=recording.recording_id,
            recording_uri=recording.uri,
            timestamp_ns=link.timestamp_ns,
            capture_timestamps_ns={
                name: mcap.capture_timestamp_ns
                for name, (mcap, _) in mcap_resolver.get_tick_channels(
                    session=session, group_sample_id=link.sample_id
                ).items()
            },
            annotations=annotations[link.sample_id],
            tags=tags.get(link.sample_id, []),
        )
        for link in links
    ]


def _annotations_by_group(
    session: Session, group_sample_ids: Sequence[UUID]
) -> defaultdict[UUID, list[AnnotationView]]:
    """Returns the annotations keyed by tick group."""
    rows = annotation_resolver.get_all_by_parent_sample_ids(
        session=session, parent_sample_ids=group_sample_ids, load_view_relationships=True
    )
    parent_track_class_names = parent_track_lookup.fetch_parent_track_class_names(
        session=session, annotations=rows
    )
    annotations: defaultdict[UUID, list[AnnotationView]] = defaultdict(list)
    for row in rows:
        annotations[row.parent_sample_id].append(
            AnnotationView.from_annotation_table(
                annotation=row, parent_track_class_names=parent_track_class_names
            )
        )
    return annotations


def _recording(session: Session, sequence_id: UUID) -> RecordingTable:
    """Returns the recording of an MCAP sequence."""
    mcap_sequence = mcap_group_sequence_resolver.get_by_id(session=session, sample_id=sequence_id)
    if mcap_sequence is None:
        raise ValueError(f"Sample {sequence_id} is not an MCAP sequence.")
    recording = recording_resolver.get_by_id(
        session=session, recording_id=mcap_sequence.recording_id
    )
    if recording is None:
        raise ValueError(f"The recording of sequence {sequence_id} was not found.")
    return recording
