"""Join annotation MCAP SceneUpdate cuboids to indexed ticks.

The annotation MCAP is not a recording. Cuboids join ticks by an exact match of
SceneEntity.timestamp to sample_sequence_link.timestamp_ns.
"""

from __future__ import annotations

import logging
from bisect import bisect_left
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from uuid import UUID

from lightly_studio.core.mcap import matching, scene_update
from lightly_studio.core.mcap.errors import McapAccessError
from lightly_studio.core.mcap.reader import McapFileReader
from lightly_studio.core.mcap.sequence import McapSequenceEntry
from lightly_studio.core.mcap.type_definitions import CuboidLabel, FrameTags, SceneUpdateLabels

logger = logging.getLogger(__name__)

DEFAULT_ANNOTATION_SOURCE = "ground_truth"
DEFAULT_EMPTY_SCENE_MAX_DIFF_NS = 50_000_000
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
    """Cuboids, tags, and empty scenes matched to groups, plus join counts."""

    cuboids_by_group: dict[UUID, list[CuboidLabel]] = field(
        default_factory=lambda: defaultdict(list)
    )
    tags_by_group: dict[UUID, FrameTags] = field(default_factory=dict)
    empty_group_ids: set[UUID] = field(default_factory=set)
    matched_count: int = 0
    unmatched_count: int = 0


def match_labels(
    messages: list[tuple[int, SceneUpdateLabels]], ticks: dict[int, UUID]
) -> MatchResult:
    """Join SceneUpdate payloads to ticks by exact entity timestamp.

    An empty scene has no entity timestamp. Its timestamp is inferred from the
    closest non-empty message's difference between entity and MCAP log clocks.
    If every scene is empty, the MCAP log time is used.
    """
    references = _timestamp_references(messages=messages)
    tick_timestamps = sorted(ticks)
    matched = MatchResult()
    for log_time_ns, labels in messages:
        _match_one_message(
            empty_scene_timestamp_ns=_empty_scene_timestamp(
                log_time_ns=log_time_ns,
                references=references,
            ),
            labels=labels,
            ticks=ticks,
            tick_timestamps=tick_timestamps,
            matched=matched,
        )
    matched.cuboids_by_group = dict(matched.cuboids_by_group)
    return matched


def log_match_summary(
    annotation_mcap_uri: str,
    matched: MatchResult,
    ticks: Mapping[int, UUID],
    messages: Sequence[tuple[int, SceneUpdateLabels]],
) -> None:
    """Log join counts and warn when most entities miss their ticks."""
    labeled_groups = (
        set(matched.cuboids_by_group) | matched.empty_group_ids | set(matched.tags_by_group)
    )
    unlabeled_ticks = len(ticks) - len(labeled_groups)
    logger.info(
        "Annotation MCAP '%s': %d matched, %d unmatched, %d ticks unlabeled.",
        annotation_mcap_uri,
        matched.matched_count,
        matched.unmatched_count,
        unlabeled_ticks,
    )
    if matched.unmatched_count > 0 and matched.unmatched_count >= matched.matched_count:
        _log_clock_mismatch(
            annotation_mcap_uri=annotation_mcap_uri, matched=matched, ticks=ticks, messages=messages
        )


def _match_one_message(
    empty_scene_timestamp_ns: int,
    labels: SceneUpdateLabels,
    ticks: dict[int, UUID],
    tick_timestamps: Sequence[int],
    matched: MatchResult,
) -> None:
    """Join one SceneUpdate to ticks."""
    if not labels.cuboids and labels.frame_tags is None:
        _match_empty_scene(
            timestamp_ns=empty_scene_timestamp_ns,
            ticks=ticks,
            tick_timestamps=tick_timestamps,
            matched=matched,
        )
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


def _match_empty_scene(
    timestamp_ns: int,
    ticks: Mapping[int, UUID],
    tick_timestamps: Sequence[int],
    matched: MatchResult,
) -> None:
    """Join an empty SceneUpdate to the nearest tick within the accepted difference."""
    match = matching.closest(max_diff_ns=DEFAULT_EMPTY_SCENE_MAX_DIFF_NS)
    index = match(timestamp_ns, tick_timestamps)
    if index is None:
        matched.unmatched_count += 1
        return
    group_id = ticks[tick_timestamps[index]]
    matched.empty_group_ids.add(group_id)
    matched.matched_count += 1


def _timestamp_references(
    messages: Sequence[tuple[int, SceneUpdateLabels]],
) -> list[tuple[int, int]]:
    """Return `(log_time, entity_time_offset)` references from non-empty scenes."""
    references = []
    for log_time_ns, labels in messages:
        timestamp_ns = _first_entity_timestamp(labels=labels)
        if timestamp_ns is not None:
            references.append((log_time_ns, timestamp_ns - log_time_ns))
    return sorted(references)


def _empty_scene_timestamp(log_time_ns: int, references: Sequence[tuple[int, int]]) -> int:
    """Infer an empty scene timestamp using the closest non-empty scene clock offset."""
    if not references:
        return log_time_ns
    index = bisect_left(references, (log_time_ns, 0))
    candidates = references[max(0, index - 1) : index + 1]
    _, offset_ns = min(candidates, key=lambda reference: abs(reference[0] - log_time_ns))
    return log_time_ns + offset_ns


def _first_entity_timestamp(labels: SceneUpdateLabels) -> int | None:
    """Return one entity timestamp to relate entity and MCAP log clocks."""
    if labels.cuboids:
        return labels.cuboids[0].timestamp_ns
    if labels.frame_tags is not None:
        return labels.frame_tags.timestamp_ns
    return None


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
