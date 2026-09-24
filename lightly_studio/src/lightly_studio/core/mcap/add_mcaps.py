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

from lightly_studio.core.file_outcome_report import (
    AlreadyPresentInputFileError,
    BrokenInputFileError,
    FileOutcomeReport,
)
from lightly_studio.core.mcap import dataset_schema, matching
from lightly_studio.core.mcap.component import McapComponentSpec
from lightly_studio.core.mcap.create_mcap import CreateMcap
from lightly_studio.core.mcap.create_sensor_calibration import CreateSensorCalibration
from lightly_studio.core.mcap.errors import McapAccessError
from lightly_studio.core.mcap.reader import McapFileReader
from lightly_studio.core.mcap.recording import Recording
from lightly_studio.core.mcap.sequence import McapSequenceEntry
from lightly_studio.core.mcap.type_definitions import CameraIntrinsics, FrameLocator
from lightly_studio.database import db_manager
from lightly_studio.models.mcap import McapCreate
from lightly_studio.resolvers import group_resolver, mcap_resolver, recording_resolver

if TYPE_CHECKING:
    from lightly_studio.core.mcap.component import McapComponent
    from lightly_studio.core.mcap.mcap_dataset import McapDataset

logger = logging.getLogger(__name__)

MCAP_EXTENSIONS = {".mcap"}
"""The file extensions an MCAP recording is discovered by."""

DEFAULT_MAX_PAIRING_DIFF_NS = 50_000_000
"""The largest time difference that still pairs a component with an sync tick."""


def index_recordings(
    dataset: McapDataset,
    mcap_paths: Iterable[str],
    sync_component: str,
    components: Sequence[McapComponentSpec],
    max_pairing_diff_ns: int = DEFAULT_MAX_PAIRING_DIFF_NS,
) -> list[UUID]:
    """Index several recordings into a dataset, one sequence each.

    A recording whose URI is already in the dataset is skipped, including a path that
    appears twice in `mcap_paths`. A recording that cannot be read is reported and the
    others are still indexed.

    Args:
        dataset: The dataset to index into.
        mcap_paths: The paths or URIs of the `.mcap` files.
        sync_component: The name of the component whose messages are the ticks.
        components: The specs the recordings are read through. They must be the
            components the dataset was created with. Topics are not stored, so they are
            passed on every call.
        max_pairing_diff_ns: The largest time difference that still pairs a component
            with an anchor tick.

    Returns:
        The sample ID of the sequence of every recording that was indexed, in the order
        the recordings were read in. A recording that failed or was already present has
        no entry.

    Raises:
        ValueError: If `components` names other components than the dataset has, or if
            `sync_component` is not one of them.
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
                    )
                )
            except McapAccessError as exc:
                raise BrokenInputFileError(f"Cannot index '{mcap_path}': {exc}") from exc
    report.raise_if_all_failed()
    report.log_summary()
    return sequence_sample_ids


def index_recording(
    dataset: McapDataset,
    mcap_path: str,
    sync_component: str,
    components: Sequence[McapComponentSpec],
    max_pairing_diff_ns: int = DEFAULT_MAX_PAIRING_DIFF_NS,
) -> UUID:
    """Index one recording into a dataset.

    Args:
        dataset: The dataset to index into.
        mcap_path: The path or URI of the `.mcap` file.
        sync_component: The name of the component whose messages are the ticks.
        components: The specs the recording is read through. They must be the components
            the dataset was created with. Topics are not stored, so they are passed on
            every call.
        max_pairing_diff_ns: The largest time difference that still pairs a component
            with an anchor tick.

    Returns:
        The sample ID of the sequence that holds the groups of the recording.

    Raises:
        ValueError: If `components` names other components than the dataset has, or if
            `sync_component` is not one of them.
        McapAccessError: If the recording cannot be read, or if it has no topic of a
            component.
    """
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
    )
    rows = _complete_rows(components=components, locators=loaded.locators)
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
                timestamp_ns=row[sync_object.name].log_time_ns,
            )
            for seq_number, (group_sample_id, row) in enumerate(zip(group_sample_ids, rows))
        ]
    )
    return sequence.sample_id


class _LoadedRecording(NamedTuple):
    """The locators of every component, paired to the sync component, plus camera intrinsics."""

    locators: dict[str, list[FrameLocator | None]]
    intrinsics: dict[str, CameraIntrinsics]


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
) -> _LoadedRecording:
    """Pair every component to the sync_component, and read the intrinsics of the cameras.

    The topics are read in a single pass, because a chunk holds the messages of every
    topic in a time span and reading them one at a time fetches the shared chunks again
    for each of them.
    """
    with McapFileReader(mcap_path) as reader:
        reader.load_data_for_topics(_topics_to_load(components=components))
        sync_locators = reader.get_frame_locators(sync_component.topic)
        anchor_timestamps_ns = [locator.log_time_ns for locator in sync_locators]

        locators: dict[str, list[FrameLocator | None]] = {sync_component.name: list(sync_locators)}
        for component in components:
            if component.name == sync_component.name:
                continue
            locators[component.name] = reader.get_frame_locators(
                component.topic,
                sync_timestamps=anchor_timestamps_ns,
                sync_rule=matching.closest(max_diff_ns=max_pairing_diff_ns),
            )

        intrinsics = {
            component.name: reader.get_intrinsic(topic=component.camera_info_topic)
            for component in components
            if component.camera_info_topic is not None
        }
    return _LoadedRecording(locators=locators, intrinsics=intrinsics)


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


def _fill_mcap_definitions(
    components: Sequence[McapComponentSpec],
    mcap_components: Mapping[str, McapComponent],
    loaded: _LoadedRecording,
) -> None:
    """Fill the channel and the frame of every component from the recording.

    Only the first recording that is indexed fills them, so all recordings of a dataset
    keep one schema.
    """
    for component in components:
        first_locator = next(
            (locator for locator in loaded.locators[component.name] if locator is not None), None
        )
        intrinsics = loaded.intrinsics.get(component.name)
        mcap_components[component.name].update_mcap_definition(
            channel_id=first_locator.channel_id if first_locator is not None else None,
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
