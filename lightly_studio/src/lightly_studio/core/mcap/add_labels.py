"""Join annotation MCAP SceneUpdate cuboids to indexed ticks and persist them.

The annotation MCAP is not a recording. Cuboids join ticks by an exact match of
SceneEntity.timestamp to sample_sequence_link.timestamp_ns.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from uuid import UUID

from sqlmodel import Session, col, func, select

from lightly_studio.core.file_outcome_report import (
    BrokenInputFileError,
    FileOutcomeReport,
    MissingInputFileError,
)
from lightly_studio.core.mcap import annotation_mcap, scene_update
from lightly_studio.core.mcap.errors import McapAccessError
from lightly_studio.core.mcap.reader import McapFileReader
from lightly_studio.core.mcap.sequence import McapSequence, McapSequenceEntry
from lightly_studio.core.mcap.type_definitions import CuboidLabel, FrameTags, SceneUpdateLabels
from lightly_studio.models.annotation.annotation_base import AnnotationCreate, AnnotationType
from lightly_studio.models.annotation.cuboid_3d import Cuboid3DCreate
from lightly_studio.models.annotation.object_track import ObjectTrackCreate, ObjectTrackTable
from lightly_studio.models.annotation_label import AnnotationLabelCreate
from lightly_studio.resolvers import (
    annotation_label_resolver,
    annotation_resolver,
    object_track_resolver,
)

if TYPE_CHECKING:
    from lightly_studio.core.mcap.mcap_dataset import McapDataset

logger = logging.getLogger(__name__)

DEFAULT_ANNOTATION_SOURCE = "ground_truth"
_DEBUG_TIMESTAMP_COUNT = 5


def read_scene_updates(annotation_mcap_uri: str, topic: str) -> list[tuple[int, SceneUpdateLabels]]:
    """Decode every SceneUpdate message in an annotation MCAP.

    Args:
        annotation_mcap_uri: The path or URI of the annotation MCAP.
        topic: The SceneUpdate topic in the annotation MCAP.

    Returns:
        `(log_time_ns, labels)` pairs, in file order.
    """
    with McapFileReader(annotation_mcap_uri) as reader:
        return [
            (log_time_ns, scene_update.from_decoded_message(decoded_message))
            for log_time_ns, decoded_message in reader.iter_decoded_messages(topic)
        ]


def ticks_by_timestamp(entries: list[McapSequenceEntry]) -> dict[int, UUID]:
    """Map unique sequence timestamps to group sample IDs. Drops ticks without a time."""
    ticks: dict[int, UUID] = {}
    for entry in entries:
        if entry.timestamp_ns is None:
            continue
        if entry.timestamp_ns in ticks:
            raise ValueError(f"Sequence has multiple ticks at timestamp {entry.timestamp_ns}.")
        ticks[entry.timestamp_ns] = entry.sample_id
    return ticks


@dataclass
class MatchResult:
    """Cuboids and tags matched to groups, plus join counts."""

    cuboids_by_group: dict[UUID, list[CuboidLabel]] = field(
        default_factory=lambda: defaultdict(list)
    )
    tags_by_group: dict[UUID, FrameTags] = field(default_factory=dict)
    empty_count: int = 0
    matched_count: int = 0
    unmatched_count: int = 0


def match_labels(
    messages: list[tuple[int, SceneUpdateLabels]], ticks: dict[int, UUID]
) -> MatchResult:
    """Join SceneUpdate payloads to ticks by exact entity timestamp.

    An empty scene has no entity timestamp, so it is counted but not joined.
    """
    matched = MatchResult()
    for _, labels in messages:
        _match_one_message(labels=labels, ticks=ticks, matched=matched)
    matched.cuboids_by_group = dict(matched.cuboids_by_group)
    return matched


def log_match_summary(
    annotation_mcap_uri: str,
    matched: MatchResult,
    ticks: Mapping[int, UUID],
    messages: Sequence[tuple[int, SceneUpdateLabels]],
) -> None:
    """Log join counts and warn when most entities miss their ticks."""
    labeled_groups = set(matched.cuboids_by_group) | set(matched.tags_by_group)
    ticks_without_entities = len(ticks) - len(labeled_groups)
    logger.info(
        "Annotation MCAP '%s': %d matched, %d unmatched, %d empty messages, "
        "%d ticks without entities.",
        annotation_mcap_uri,
        matched.matched_count,
        matched.unmatched_count,
        matched.empty_count,
        ticks_without_entities,
    )
    if matched.unmatched_count > 0 and matched.unmatched_count >= matched.matched_count:
        _log_clock_mismatch(
            annotation_mcap_uri=annotation_mcap_uri, matched=matched, ticks=ticks, messages=messages
        )


def write_sequence_labels(
    dataset: McapDataset,
    sequence: McapSequence,
    annotation_mcap_uri: str,
    messages: list[tuple[int, SceneUpdateLabels]],
    annotation_source: str = DEFAULT_ANNOTATION_SOURCE,
) -> None:
    """Match annotation MCAP messages to ticks and persist cuboids and object tracks."""
    session = dataset.group_dataset.session
    ticks = ticks_by_timestamp(entries=sequence.get_samples())
    matched = match_labels(messages=messages, ticks=ticks)
    log_match_summary(
        annotation_mcap_uri=annotation_mcap_uri, matched=matched, ticks=ticks, messages=messages
    )
    track_ids = _allocate_tracks(session=session, dataset_id=dataset.dataset_id, matched=matched)
    annotations = _annotation_creates(
        session=session, dataset_id=dataset.dataset_id, matched=matched, track_ids=track_ids
    )
    if annotations:
        annotation_resolver.create_many(
            session=session,
            parent_collection_id=dataset.group_dataset.collection_id,
            annotations=annotations,
            collection_name=annotation_source,
        )
    session.commit()


def add_labels_from_annotation_mcaps(
    dataset: McapDataset,
    topic: str,
    suffix: str = annotation_mcap.DEFAULT_ANNOTATION_MCAP_SUFFIX,
    annotation_source: str = DEFAULT_ANNOTATION_SOURCE,
) -> None:
    """Read cuboids from each sequence's annotation MCAP and store them on tick groups.

    A recording with no annotation MCAP is skipped. An unreadable annotation MCAP is
    reported and the other sequences still run. Missing annotation MCAPs are normal and
    do not fail the run.

    Args:
        dataset: The dataset whose sequences receive annotations.
        topic: The SceneUpdate topic in the annotation MCAP.
        suffix: Inserted before `.mcap` to form the annotation MCAP URI.
        annotation_source: Name of the annotation source that stores the cuboids.
    """
    report = FileOutcomeReport()
    for sequence in dataset.get_sequences():
        recording = dataset.get_recording(recording_id=sequence.recording_id)
        annotation_mcap_path = annotation_mcap.annotation_mcap_uri(
            recording_uri=recording.uri, suffix=suffix
        )
        with report.track(annotation_mcap_path):
            _add_labels_for_sequence(
                dataset=dataset,
                sequence=sequence,
                annotation_mcap_uri=annotation_mcap_path,
                topic=topic,
                annotation_source=annotation_source,
            )
    report.log_summary()


def _add_labels_for_sequence(
    dataset: McapDataset,
    sequence: McapSequence,
    annotation_mcap_uri: str,
    topic: str,
    annotation_source: str,
) -> None:
    """Persist cuboids on one sequence from its annotation MCAP.

    Raises:
        MissingInputFileError: If the annotation MCAP is not present.
        BrokenInputFileError: If the annotation MCAP cannot be read.
    """
    if not annotation_mcap.annotation_mcap_exists(uri=annotation_mcap_uri):
        raise MissingInputFileError(f"No annotation MCAP at '{annotation_mcap_uri}'.")
    try:
        messages = read_scene_updates(annotation_mcap_uri=annotation_mcap_uri, topic=topic)
        write_sequence_labels(
            dataset=dataset,
            sequence=sequence,
            annotation_mcap_uri=annotation_mcap_uri,
            messages=messages,
            annotation_source=annotation_source,
        )
    except (McapAccessError, ValueError) as error:
        raise BrokenInputFileError(
            f"Cannot add annotations from '{annotation_mcap_uri}': {error}"
        ) from error


def _match_one_message(
    labels: SceneUpdateLabels,
    ticks: dict[int, UUID],
    matched: MatchResult,
) -> None:
    """Join one SceneUpdate to ticks."""
    if not labels.cuboids and labels.frame_tags is None:
        matched.empty_count += 1
        return
    for cuboid in labels.cuboids:
        group_id = ticks.get(cuboid.timestamp_ns)
        if group_id is None:
            matched.unmatched_count += 1
            continue
        matched.cuboids_by_group[group_id].append(cuboid)
        matched.matched_count += 1
    if labels.frame_tags is not None:
        group_id = ticks.get(labels.frame_tags.timestamp_ns)
        if group_id is None:
            matched.unmatched_count += 1
        else:
            if group_id in matched.tags_by_group:
                raise McapAccessError("Multiple frame tag entities match the same group.")
            matched.tags_by_group[group_id] = labels.frame_tags
            matched.matched_count += 1


def _log_clock_mismatch(
    annotation_mcap_uri: str,
    matched: MatchResult,
    ticks: Mapping[int, UUID],
    messages: Sequence[tuple[int, SceneUpdateLabels]],
) -> None:
    """Log the tick and entity clocks so a mismatch can be compared by hand."""
    tick_times = sorted(ticks)
    entity_times = _entity_timestamps(messages=messages)
    logger.warning(
        "Clock mismatch for annotation MCAP '%s': SceneEntity.timestamp must equal "
        "sample_sequence_link.timestamp_ns (%d matched, %d unmatched). "
        "Tick range [%s, %s], entity range [%s, %s], first ticks %s, "
        "first entity timestamps %s, first message log times %s.",
        annotation_mcap_uri,
        matched.matched_count,
        matched.unmatched_count,
        tick_times[0] if tick_times else None,
        tick_times[-1] if tick_times else None,
        min(entity_times) if entity_times else None,
        max(entity_times) if entity_times else None,
        tick_times[:_DEBUG_TIMESTAMP_COUNT],
        entity_times[:_DEBUG_TIMESTAMP_COUNT],
        [log_time_ns for log_time_ns, _ in messages[:_DEBUG_TIMESTAMP_COUNT]],
    )


def _entity_timestamps(messages: Sequence[tuple[int, SceneUpdateLabels]]) -> list[int]:
    """Collect SceneEntity timestamps from cuboids and frame tags."""
    timestamps: list[int] = []
    for _, labels in messages:
        timestamps.extend(cuboid.timestamp_ns for cuboid in labels.cuboids)
        if labels.frame_tags is not None:
            timestamps.append(labels.frame_tags.timestamp_ns)
    return timestamps


def _allocate_tracks(session: Session, dataset_id: UUID, matched: MatchResult) -> dict[int, UUID]:
    """Create a dataset-unique track for each source_track_id and link it to its parent track.

    A parent track id without cuboids of its own also gets a track. Parent tracks must be
    root tracks. Roots are created before children, so the parent foreign key resolves.

    Raises:
        ValueError: If a track has more than one parent, or a parent track has a parent.
    """
    parent_by_source = _parent_by_source_track(matched=matched)
    if not parent_by_source:
        return {}

    roots = [source_id for source_id, parent_id in parent_by_source.items() if parent_id is None]
    children = [
        (source_id, parent_id)
        for source_id, parent_id in parent_by_source.items()
        if parent_id is not None
    ]
    root_ids = set(roots)
    if any(parent_id not in root_ids for _, parent_id in children):
        raise ValueError("A parent track must not have a parent track itself.")

    next_number = _next_track_number(session=session, dataset_id=dataset_id)
    track_ids = _create_source_tracks(
        session=session,
        dataset_id=dataset_id,
        next_number=next_number,
        links=[(source_id, None) for source_id in roots],
    )
    if children:
        track_ids.update(
            _create_source_tracks(
                session=session,
                dataset_id=dataset_id,
                next_number=next_number + len(roots),
                links=[(source_id, track_ids[parent_id]) for source_id, parent_id in children],
            )
        )
    return track_ids


def _parent_by_source_track(matched: MatchResult) -> dict[int, int | None]:
    """Map each source_track_id, including parent-only ids, to its parent source_track_id.

    Raises:
        ValueError: If cuboids of one track have different parent track ids.
    """
    parent_by_source: dict[int, int | None] = {}
    for cuboids in matched.cuboids_by_group.values():
        for cuboid in cuboids:
            parent_id = parent_by_source.setdefault(cuboid.track_id, cuboid.parent_track_id)
            if parent_id != cuboid.parent_track_id:
                raise ValueError(f"Track {cuboid.track_id} has more than one parent track id.")
    for parent_id in list(parent_by_source.values()):
        if parent_id is not None:
            parent_by_source.setdefault(parent_id, None)
    return parent_by_source


def _create_source_tracks(
    session: Session,
    dataset_id: UUID,
    next_number: int,
    links: Sequence[tuple[int, UUID | None]],
) -> dict[int, UUID]:
    """Insert tracks and map each source_track_id to its object_track_id."""
    created_ids = object_track_resolver.create_many(
        session=session,
        tracks=[
            ObjectTrackCreate(
                object_track_number=next_number + index,
                dataset_id=dataset_id,
                source_track_id=source_id,
                parent_object_track_id=parent_object_track_id,
            )
            for index, (source_id, parent_object_track_id) in enumerate(links)
        ],
    )
    return {
        source_id: object_track_id for (source_id, _), object_track_id in zip(links, created_ids)
    }


def _next_track_number(session: Session, dataset_id: UUID) -> int:
    """Return the next dataset-unique object_track_number."""
    maximum = session.exec(
        select(func.max(ObjectTrackTable.object_track_number)).where(
            col(ObjectTrackTable.dataset_id) == dataset_id
        )
    ).one()
    return 1 if maximum is None else maximum + 1


def _annotation_creates(
    session: Session,
    dataset_id: UUID,
    matched: MatchResult,
    track_ids: dict[int, UUID],
) -> list[AnnotationCreate]:
    """Build AnnotationCreate rows for matched cuboids."""
    label_ids = _label_ids_for_cuboids(
        session=session, dataset_id=dataset_id, cuboids_by_group=matched.cuboids_by_group
    )
    return [
        AnnotationCreate(
            annotation_label_id=label_ids[cuboid.class_name],
            annotation_type=AnnotationType.CUBOID_3D,
            parent_sample_id=group_id,
            object_track_id=track_ids[cuboid.track_id],
            cuboid_3d=_cuboid_create(cuboid=cuboid),
        )
        for group_id, cuboids in matched.cuboids_by_group.items()
        for cuboid in cuboids
    ]


def _cuboid_create(cuboid: CuboidLabel) -> Cuboid3DCreate:
    """Map a decoded cuboid onto the persist model."""
    return Cuboid3DCreate(
        frame_id=cuboid.frame_id,
        px=cuboid.position[0],
        py=cuboid.position[1],
        pz=cuboid.position[2],
        qx=cuboid.rotation[0],
        qy=cuboid.rotation[1],
        qz=cuboid.rotation[2],
        qw=cuboid.rotation[3],
        sx=cuboid.size[0],
        sy=cuboid.size[1],
        sz=cuboid.size[2],
        interpolated=cuboid.interpolated,
    )


def _label_ids_for_cuboids(
    session: Session, dataset_id: UUID, cuboids_by_group: dict[UUID, list[CuboidLabel]]
) -> dict[str, UUID]:
    """Get or create annotation classes for the cuboid class names."""
    class_names = {cuboid.class_name for cuboids in cuboids_by_group.values() for cuboid in cuboids}
    return {
        class_name: _get_or_create_label_id(
            session=session, dataset_id=dataset_id, class_name=class_name
        )
        for class_name in class_names
    }


def _get_or_create_label_id(session: Session, dataset_id: UUID, class_name: str) -> UUID:
    """Return the annotation label ID for a class, creating it if needed."""
    label = annotation_label_resolver.get_by_label_name(
        session=session, dataset_id=dataset_id, label_name=class_name
    )
    if label is not None:
        return label.annotation_label_id
    created = annotation_label_resolver.create(
        session=session,
        label=AnnotationLabelCreate(dataset_id=dataset_id, annotation_label_name=class_name),
    )
    return created.annotation_label_id
