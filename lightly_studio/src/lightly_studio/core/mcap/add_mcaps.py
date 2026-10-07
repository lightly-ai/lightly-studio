"""Functions to index MCAP recordings into a dataset in the database.

One recording becomes one sequence of groups: every message of the sync component is
a tick, the other components are paired against it, and a tick that any component
cannot be paired to is dropped, so every group that is written is complete.

The writes are batched, so a recording costs a handful of commits rather than a few per
tick.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping, Sequence
from typing import TYPE_CHECKING, NamedTuple
from uuid import UUID

from mcap.exceptions import McapError

from lightly_studio.core.file_outcome_report import (
    AlreadyPresentInputFileError,
    BrokenInputFileError,
    FileOutcomeReport,
    MissingInputFileError,
)
from lightly_studio.core.mcap import dataset_schema, matching, reference_frames
from lightly_studio.core.mcap.component import McapComponentSpec
from lightly_studio.core.mcap.create_mcap import CreateMcap
from lightly_studio.core.mcap.create_sensor_calibration import CreateSensorCalibration
from lightly_studio.core.mcap.errors import McapAccessError, TopicNotFoundError
from lightly_studio.core.mcap.reader import STATIC_TRANSFORM_TOPIC, McapFileReader
from lightly_studio.core.mcap.recording import Recording
from lightly_studio.core.mcap.sequence import McapSequenceEntry
from lightly_studio.core.mcap.type_definitions import (
    CameraIntrinsics,
    FrameLocator,
    StaticTransform,
)
from lightly_studio.database import db_manager
from lightly_studio.models.mcap import McapCreate
from lightly_studio.resolvers import group_resolver, mcap_resolver, recording_resolver

if TYPE_CHECKING:
    from lightly_studio.core.mcap.component import McapComponent
    from lightly_studio.core.mcap.mcap_dataset import McapDataset

logger = logging.getLogger(__name__)

MCAP_EXTENSION = ".mcap"
MCAP_EXTENSIONS = {MCAP_EXTENSION}
"""The file extensions an MCAP recording is discovered by."""

DEFAULT_MAX_PAIRING_DIFF_NS = 50_000_000
"""The largest time difference that still pairs a component with an sync tick."""


def index_recordings(  # noqa: PLR0913
    dataset: McapDataset,
    mcap_paths: Iterable[str],
    sync_component: str,
    components: Sequence[McapComponentSpec],
    max_pairing_diff_ns: int = DEFAULT_MAX_PAIRING_DIFF_NS,
    reference_frame_ids: Sequence[str] | None = None,
) -> list[UUID]:
    """Index several recordings into a dataset, one sequence each.

    A recording whose URI is already in the dataset is skipped, including a path that
    appears twice in `mcap_paths`. A recording that cannot be indexed, e.g. because the
    file is missing, is not an MCAP file or lacks a topic of a component, is logged with
    the reason and the others are still indexed.

    Args:
        dataset: The dataset to index into.
        mcap_paths: The paths or URIs of the `.mcap` files.
        sync_component: The name of the component whose messages are the ticks.
        components: The specs the recordings are read through. They must be the
            components the dataset was created with. Topics are not stored, so they are
            passed on every call.
        max_pairing_diff_ns: The largest time difference that still pairs a component
            with an anchor tick.
        reference_frame_ids: The coordinate frames shown in the viewer, in menu order.
            The first is the default. Each id is the frame string from the bag, for
            example `map` or `CABIN`. When omitted, no frames are stored and the
            viewer keeps each point cloud in its sensor frame.

    Returns:
        The sample ID of the sequence of every recording that was indexed, in the order
        the recordings were read in. A recording that failed or was already present has
        no entry.

    Raises:
        ValueError: If `components` names other components than the dataset has, if
            `sync_component` is not one of them, or if a reference frame id is empty
            or repeated. `index_recording` checks the reference frame ids, so they
            are checked only when a recording is indexed.
        AllInputFilesFailedError: If at least one recording was attempted and every
            attempted recording failed.
    """
    dataset_schema.check_components_match(
        session=dataset.group_dataset.session,
        group_collection_id=dataset.group_dataset.collection_id,
        components=components,
        dataset_name=dataset.name,
    )
    report = FileOutcomeReport()
    sequence_sample_ids: list[UUID] = []
    # The set starts with URIs already in the dataset and grows with URIs seen in this
    # call, so both already-present and in-run duplicate paths are skipped.
    seen_or_existing_uris = _existing_uris(dataset=dataset)
    for mcap_path in mcap_paths:
        with report.track(mcap_path):
            if mcap_path in seen_or_existing_uris:
                raise AlreadyPresentInputFileError()
            seen_or_existing_uris.add(mcap_path)
            try:
                sequence_sample_ids.append(
                    index_recording(
                        dataset=dataset,
                        mcap_path=mcap_path,
                        sync_component=sync_component,
                        components=components,
                        max_pairing_diff_ns=max_pairing_diff_ns,
                        reference_frame_ids=reference_frame_ids,
                    )
                )
            except FileNotFoundError as exc:
                logger.error("Cannot index '%s': the file does not exist.", mcap_path)
                raise MissingInputFileError() from exc
            except (McapAccessError, McapError) as exc:
                # The report only counts the failure, so the reason is logged here.
                logger.error("Cannot index '%s': %s", mcap_path, exc)
                raise BrokenInputFileError() from exc
    report.raise_if_all_failed()
    report.log_summary()
    return sequence_sample_ids


def index_recording(  # noqa: PLR0913
    dataset: McapDataset,
    mcap_path: str,
    sync_component: str,
    components: Sequence[McapComponentSpec],
    max_pairing_diff_ns: int = DEFAULT_MAX_PAIRING_DIFF_NS,
    reference_frame_ids: Sequence[str] | None = None,
) -> UUID:
    """Index one recording into a dataset.

    Sequence timestamps are the capture time of the sync component.

    Args:
        dataset: The dataset to index into.
        mcap_path: The path or URI of the `.mcap` file.
        sync_component: The name of the component whose messages are the ticks.
        components: The specs the recording is read through. They must be the components
            the dataset was created with. Topics are not stored, so they are passed on
            every call.
        max_pairing_diff_ns: The largest time difference that still pairs a component
            with an anchor tick.
        reference_frame_ids: The coordinate frames shown in the viewer, in menu order.
            The first is the default. Each id is the frame string from the bag, for
            example `map` or `CABIN`. When omitted, no frames are stored and the
            viewer keeps each point cloud in its sensor frame.

    Returns:
        The sample ID of the sequence that holds the groups of the recording.

    Raises:
        ValueError: If `components` names other components than the dataset has, if
            `sync_component` is not one of them, or if a reference frame id is empty
            or repeated.
        McapAccessError: If the recording cannot be read, if it has no topic of a
            component, if the sync component has no usable message, or if a reference
            frame is not in the recording. A recording where no tick has a message for
            every component is indexed as an empty sequence, with a warning.
        mcap.exceptions.McapError: If the file is not an MCAP file.
        FileNotFoundError: If the file does not exist.
    """
    reference_frames.check_reference_frame_ids(frame_ids=reference_frame_ids)
    dataset_schema.check_components_match(
        session=dataset.group_dataset.session,
        group_collection_id=dataset.group_dataset.collection_id,
        components=components,
        dataset_name=dataset.name,
    )
    sync_object = _get_sync_component(components=components, sync_component=sync_component)
    mcap_components = _mcap_components(dataset=dataset, components=components)

    loaded = _read_recording(
        mcap_path=mcap_path,
        components=components,
        sync_component=sync_object,
        max_pairing_diff_ns=max_pairing_diff_ns,
        reference_frame_ids=reference_frame_ids,
    )
    # Resolved before anything is written, so an unknown frame leaves no rows behind.
    frame_ids = _reference_frame_ids(loaded=loaded, reference_frame_ids=reference_frame_ids)
    rows = _complete_rows(components=components, locators=loaded.locators)
    if not loaded.locators[sync_object.name]:
        raise McapAccessError(
            f"No usable message on topic '{sync_object.topic}' of the sync component "
            f"'{sync_object.name}' in '{mcap_path}'. A message needs a decodable payload "
            "and a header stamp."
        )
    if not rows:
        logger.warning(
            _no_complete_tick_message(
                mcap_path=mcap_path,
                components=components,
                sync_component=sync_object,
                locators=loaded.locators,
                max_pairing_diff_ns=max_pairing_diff_ns,
            )
        )
    logger.info(
        "Indexing %d of %d ticks of '%s'.",
        len(rows),
        len(loaded.locators[sync_object.name]),
        mcap_path,
    )

    recording = dataset.create_recording(uri=mcap_path)
    _add_calibrations(
        recording=recording,
        components=components,
        mcap_components=mcap_components,
        loaded=loaded,
    )
    _add_static_transforms(recording=recording, static_transforms=loaded.static_transforms)
    recording.set_reference_frame_ids(frame_ids=frame_ids)
    _fill_mcap_definitions(components=components, mcap_components=mcap_components, loaded=loaded)

    sequence = dataset.create_sequence(recording_id=recording.recording_id)
    group_sample_ids = _write_groups(
        dataset=dataset, components=components, mcap_components=mcap_components, rows=rows
    )
    sequence.add_samples(
        entries=[
            McapSequenceEntry(
                sample_id=group_sample_id,
                seq_number=seq_number,
                timestamp_ns=row[sync_object.name].capture_timestamp_ns,
            )
            for seq_number, (group_sample_id, row) in enumerate(zip(group_sample_ids, rows))
        ]
    )
    return sequence.sample_id


class _LoadedRecording(NamedTuple):
    """Locators paired to the sync component, plus camera intrinsics and static transforms.

    `channel_ids` comes from the file summary, so a component still has a channel even
    when pairing finds no tick for it.
    """

    locators: dict[str, list[FrameLocator | None]]
    intrinsics: dict[str, CameraIntrinsics]
    channel_ids: dict[str, int]
    static_transforms: list[StaticTransform]
    dynamic_edges: list[tuple[str, str]]


def _get_sync_component(
    components: Sequence[McapComponentSpec], sync_component: str
) -> McapComponentSpec:
    """Return the component whose messages are the ticks of the sequence.

    Raises:
        ValueError: If no component has that name.
    """
    for component in components:
        if component.name == sync_component:
            return component
    known_names = ", ".join(component.name for component in components)
    raise ValueError(
        f"sync_component '{sync_component}' is not a component of the dataset. "
        f"Known components: {known_names}."
    )


def _read_recording(
    mcap_path: str,
    components: Sequence[McapComponentSpec],
    sync_component: McapComponentSpec,
    max_pairing_diff_ns: int,
    reference_frame_ids: Sequence[str] | None,
) -> _LoadedRecording:
    """Pair every component to the sync_component, and read intrinsics and transforms.

    Pairing uses capture timestamps first, then log times when the capture clocks do
    not overlap. The topics, including `/tf_static`, are read in a single pass, because
    a chunk holds the messages of every topic in a time span and reading them one at a
    time fetches the shared chunks again for each of them. `/tf` is read only when
    reference frames are requested, and only until those frames have been seen.
    """
    with McapFileReader(mcap_path) as reader:
        _check_topics_present(reader=reader, components=components)
        reader.load_data_for_topics(
            _topics_to_load(components=components),
            static_transform_topic=STATIC_TRANSFORM_TOPIC,
        )
        sync_locators = reader.get_frame_locators(sync_component.topic)

        locators: dict[str, list[FrameLocator | None]] = {sync_component.name: list(sync_locators)}
        for component in components:
            if component.name == sync_component.name:
                continue
            locators[component.name] = _pair_to_sync(
                reader=reader,
                topic=component.topic,
                sync_locators=sync_locators,
                max_pairing_diff_ns=max_pairing_diff_ns,
            )

        intrinsics = {
            component.name: reader.get_intrinsic(topic=component.camera_info_topic)
            for component in components
            if component.camera_info_topic is not None
        }
        channel_ids = _channel_ids_by_component(reader=reader, components=components)
        static_transforms = _named_static_transforms(
            static_transforms=reader.get_static_transforms(), mcap_path=mcap_path
        )
        dynamic_edges = _dynamic_edges(
            reader=reader,
            static_transforms=static_transforms,
            reference_frame_ids=reference_frame_ids,
        )
    return _LoadedRecording(
        locators=locators,
        intrinsics=intrinsics,
        channel_ids=channel_ids,
        static_transforms=static_transforms,
        dynamic_edges=dynamic_edges,
    )


def _check_topics_present(reader: McapFileReader, components: Sequence[McapComponentSpec]) -> None:
    """Check that the file has the topics of every component.

    Raises:
        TopicNotFoundError: If topics are missing. The error names all of them, and the
            topics the file has.
    """
    available = {topic_info.name for topic_info in reader.get_topics()}
    missing: list[str] = []
    for component in components:
        if component.topic not in available:
            missing.append(f"'{component.topic}' (component '{component.name}')")
        if component.camera_info_topic is not None and component.camera_info_topic not in available:
            missing.append(
                f"'{component.camera_info_topic}' (camera info of component '{component.name}')"
            )
    if missing:
        raise TopicNotFoundError(
            f"MCAP file '{reader.path}' has no topic {', '.join(missing)}. "
            f"Topics in the file: {', '.join(sorted(available)) or 'none'}."
        )


def _no_complete_tick_message(
    mcap_path: str,
    components: Sequence[McapComponentSpec],
    sync_component: McapComponentSpec,
    locators: Mapping[str, Sequence[FrameLocator | None]],
    max_pairing_diff_ns: int,
) -> str:
    """Explain why no tick of the recording has a message for every component."""
    unpaired = [
        component.name
        for component in components
        if all(locator is None for locator in locators[component.name])
    ]
    if unpaired:
        return (
            f"No message of component(s) {', '.join(repr(name) for name in unpaired)} in "
            f"'{mcap_path}' is within {max_pairing_diff_ns} ns of a message of the sync "
            f"component '{sync_component.name}'. Check that the topics have messages and "
            "increase `max_pairing_diff_ns` if their clocks differ."
        )
    return (
        f"No tick of '{mcap_path}' has a message for every component within "
        f"{max_pairing_diff_ns} ns of the sync component '{sync_component.name}'. "
        "Increase `max_pairing_diff_ns` or check the topics."
    )


def _pair_to_sync(
    reader: McapFileReader,
    topic: str,
    sync_locators: Sequence[FrameLocator],
    max_pairing_diff_ns: int,
) -> list[FrameLocator | None]:
    """Pair a topic to the sync component by capture time, then by log time for misses."""
    return reader.get_frame_locators(
        topic,
        sync_timestamps=[locator.capture_timestamp_ns for locator in sync_locators],
        sync_rule=matching.closest(max_diff_ns=max_pairing_diff_ns),
        fallback_timestamps=[locator.log_time_ns for locator in sync_locators],
    )


def _channel_ids_by_component(
    reader: McapFileReader, components: Sequence[McapComponentSpec]
) -> dict[str, int]:
    """Return the MCAP channel of each component's topic in the file."""
    channel_id_by_topic: dict[str, int] = {}
    for topic_info in reader.get_topics():
        channel_id_by_topic.setdefault(topic_info.name, topic_info.channel_id)
    return {component.name: channel_id_by_topic[component.topic] for component in components}


def _topics_to_load(components: Sequence[McapComponentSpec]) -> list[str]:
    """Return the data topics of the components, plus the camera info topics."""
    topics = [component.topic for component in components]
    topics.extend(
        component.camera_info_topic
        for component in components
        if component.camera_info_topic is not None
    )
    return topics


def _complete_rows(
    components: Sequence[McapComponentSpec],
    locators: Mapping[str, Sequence[FrameLocator | None]],
) -> list[dict[str, FrameLocator]]:
    """Keep the ticks that have a locator for every component.

    A group with a missing component would show a hole in the viewer, so a tick that
    any component cannot be paired to is dropped instead.
    """
    names = [component.name for component in components]
    rows: list[dict[str, FrameLocator]] = []
    for tick in zip(*(locators[name] for name in names)):
        row = {name: locator for name, locator in zip(names, tick) if locator is not None}
        if len(row) == len(names):
            rows.append(row)
    return rows


def _add_calibrations(
    recording: Recording,
    components: Sequence[McapComponentSpec],
    mcap_components: Mapping[str, McapComponent],
    loaded: _LoadedRecording,
) -> None:
    """Store the intrinsics of the cameras of the recording, if it has any."""
    calibrations = [
        CreateSensorCalibration.from_camera_intrinsics(
            collection_id=mcap_components[component.name].collection_id,
            intrinsics=loaded.intrinsics[component.name],
        )
        for component in components
        if component.is_camera
    ]
    if calibrations:
        recording.add_sensor_calibrations(calibrations=calibrations)


def _add_static_transforms(
    recording: Recording, static_transforms: Sequence[StaticTransform]
) -> None:
    """Store the static transforms of the recording, if it has any.

    A later message for the same child frame replaces the earlier edge, which is how
    the transform tree composes `/tf_static`.
    """
    edges = _latest_static_transform_per_child(static_transforms)
    if edges:
        recording.add_static_transforms(transforms=edges)


def _dynamic_edges(
    reader: McapFileReader,
    static_transforms: Sequence[StaticTransform],
    reference_frame_ids: Sequence[str] | None,
) -> list[tuple[str, str]]:
    """Return dynamic edges that cover the requested frames missing from the static tree.

    No `/tf` messages are read when no frames are requested, or when every requested
    frame is already a parent or a child of a static transform.
    """
    if not reference_frame_ids:
        return []
    known = {
        frame_id
        for transform in static_transforms
        for frame_id in (transform.parent_frame_id, transform.child_frame_id)
    }
    missing = [frame_id for frame_id in reference_frame_ids if frame_id not in known]
    if not missing:
        return []
    return reader.read_dynamic_edges_until(frame_ids=missing)


def _reference_frame_ids(
    loaded: _LoadedRecording,
    reference_frame_ids: Sequence[str] | None,
) -> list[str]:
    """Return the frames the scene of the recording can be shown in.

    None are returned when `reference_frame_ids` is not given.

    Raises:
        McapAccessError: If a frame of `reference_frame_ids` is not in the recording.
    """
    if reference_frame_ids is None:
        return []
    return reference_frames.known_reference_frame_ids(
        frame_ids=reference_frame_ids,
        static_transforms=_latest_static_transform_per_child(loaded.static_transforms),
        dynamic_edges=loaded.dynamic_edges,
    )


def _latest_static_transform_per_child(
    static_transforms: Sequence[StaticTransform],
) -> list[StaticTransform]:
    """Keep the last transform of each child frame."""
    latest_by_child: dict[str, StaticTransform] = {}
    for transform in static_transforms:
        latest_by_child[transform.child_frame_id] = transform
    return list(latest_by_child.values())


def _named_static_transforms(
    static_transforms: Sequence[StaticTransform], mcap_path: str
) -> list[StaticTransform]:
    """Drop the transforms that have an empty parent or child frame id.

    Such an edge cannot be stored or looked up. The rest of the recording is still
    indexed.
    """
    named = [
        transform
        for transform in static_transforms
        if transform.parent_frame_id.strip() and transform.child_frame_id.strip()
    ]
    if len(named) < len(static_transforms):
        logger.warning(
            "Skipping %d static transforms without a frame id in '%s'.",
            len(static_transforms) - len(named),
            mcap_path,
        )
    return named


def _fill_mcap_definitions(
    components: Sequence[McapComponentSpec],
    mcap_components: Mapping[str, McapComponent],
    loaded: _LoadedRecording,
) -> None:
    """Fill the channel and the frame of every component from the recording.

    The channel comes from the topic in the file, even when pairing finds no tick for
    that component. Only the first recording that is indexed fills them, so all
    recordings of a dataset keep one schema.
    """
    for component in components:
        intrinsics = loaded.intrinsics.get(component.name)
        mcap_components[component.name].update_mcap_definition(
            channel_id=loaded.channel_ids[component.name],
            frame_id=intrinsics.frame_id if intrinsics is not None else component.frame_id,
        )


def _write_groups(
    dataset: McapDataset,
    components: Sequence[McapComponentSpec],
    mcap_components: Mapping[str, McapComponent],
    rows: Sequence[Mapping[str, FrameLocator]],
) -> list[UUID]:
    """Write the locators of every component and the groups that hold them.

    The locators of one component are written in a single call, so a recording costs one
    call per component rather than one per tick.

    Returns:
        The IDs of the group samples, in the order of `rows`.
    """
    session = dataset.group_dataset.session
    sample_ids_by_component = {
        component.name: mcap_resolver.create_many(
            session=session,
            collection_id=mcap_components[component.name].collection_id,
            samples=[_mcap_create(locator=row[component.name]) for row in rows],
        )
        for component in components
    }
    return group_resolver.create_many(
        session=session,
        collection_id=dataset.group_dataset.collection_id,
        groups=[
            {sample_ids_by_component[component.name][index] for component in components}
            for index in range(len(rows))
        ],
    )


def _mcap_create(locator: FrameLocator) -> McapCreate:
    """Build the row of one locator from the reader factory."""
    creator = CreateMcap.from_frame_locator(locator=locator)
    return McapCreate(
        channel_id=creator.channel_id,
        log_time_ns=creator.log_time_ns,
        capture_timestamp_ns=creator.capture_timestamp_ns,
        keyframe_log_time_ns=creator.keyframe_log_time_ns,
    )


def _mcap_components(
    dataset: McapDataset, components: Sequence[McapComponentSpec]
) -> dict[str, McapComponent]:
    """Look up each component once so indexing does not re-query the group schema."""
    return {
        component.name: dataset.group_dataset.get_component(name=component.name)
        for component in components
    }


def _existing_uris(dataset: McapDataset) -> set[str]:
    """Return the URIs of recordings already indexed into the dataset."""
    recordings = recording_resolver.get_all_by_dataset_id(
        session=db_manager.persistent_session(), dataset_id=dataset.dataset_id
    )
    return {recording.uri for recording in recordings}
