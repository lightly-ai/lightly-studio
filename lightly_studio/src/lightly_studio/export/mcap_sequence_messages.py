"""Builds the SceneUpdate messages of one MCAP sequence, straight from the database."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from uuid import UUID

from mcap.exceptions import McapError
from sqlmodel import Session

from lightly_studio.core.mcap.errors import McapAccessError, TransformNotFoundError
from lightly_studio.core.mcap.reader import McapFileReader, calibration
from lightly_studio.core.mcap.type_definitions import (
    CuboidLabel,
    FrameTags,
    SceneUpdateLabels,
    StaticTransform,
)
from lightly_studio.errors import ExportError
from lightly_studio.models.annotation.annotation_base import AnnotationType, AnnotationView
from lightly_studio.models.mcap import McapTable
from lightly_studio.models.recording import RecordingTable
from lightly_studio.resolvers import (
    annotation_resolver,
    mcap_resolver,
    sequence_resolver,
    tag_resolver,
)
from lightly_studio.services.recording_service import (
    cuboids_in_frame,
    load_dynamic_transforms,
    load_static_transforms,
    reader_cache,
)
from lightly_studio.services.recording_service.load_dynamic_transforms import (
    DynamicTransformsByTime,
)


@dataclass(frozen=True)
class _Tick:
    """One tick of a sequence.

    Attributes:
        sample_id: The group sample of the tick.
        timestamp_ns: The sweep timestamp of the tick.
        log_time_ns: The log time of the tick's SceneUpdate message.
    """

    sample_id: UUID
    timestamp_ns: int
    log_time_ns: int


@dataclass(frozen=True)
class _RecordingTransforms:
    """The transforms that every tick of a sequence maps its cuboids with.

    Attributes:
        uri: The URI of the recording, to read it and to name it in error messages.
        static_transforms: The static edges stored for the recording.
        dynamic_transforms: The dynamic edges stored for the ticks, or `None` if the
            recording has no stored dynamic transforms and they are read from the file.
    """

    uri: str
    static_transforms: Sequence[StaticTransform]
    dynamic_transforms: DynamicTransformsByTime | None


def build_sequence_messages(
    session: Session,
    recording: RecordingTable,
    sequence_id: UUID,
    annotation_collection_id: UUID,
    target_frame_id: str,
) -> list[tuple[int, SceneUpdateLabels]]:
    """Builds the SceneUpdate messages of one MCAP sequence, straight from the database.

    The ticks, cuboids, tags and transforms of the sequence are loaded in bulk, not
    per tick.

    Args:
        session: The database session.
        recording: The recording the sequence was indexed from.
        sequence_id: The sequence sample ID.
        annotation_collection_id: The annotation source to export cuboids from. Cuboids in
            other annotation sources of the same ticks are ignored.
        target_frame_id: The coordinate frame every cuboid is mapped into.

    Returns:
        One `(log_time_ns, labels)` entry per tick, in `seq_number` order. The track ids
        of a cuboid are the `object_track_number`s of its track and parent track. The
        cuboids of a message are sorted by track id, then by class name, then by
        annotation ID. Every `CuboidLabel.frame_id` in the result equals
        `target_frame_id`.

    Raises:
        ExportError: If a tick has no timestamp, a cuboid has no frame or track, or no
            chain of transforms connects a cuboid's frame to `target_frame_id`.
    """
    ticks = _load_ticks(session=session, sequence_id=sequence_id)
    if not ticks:
        return []
    sample_ids = [tick.sample_id for tick in ticks]
    views_by_sample_id = _map_to_target_frame(
        session=session,
        recording=recording,
        ticks=ticks,
        views_by_sample_id=_load_cuboid_views(
            session=session,
            sample_ids=sample_ids,
            annotation_collection_id=annotation_collection_id,
        ),
        target_frame_id=target_frame_id,
    )
    tag_names_by_sample_id = tag_resolver.get_names_by_sample_ids(
        session=session, sample_ids=sample_ids
    )
    return [
        _tick_message(
            tick=tick,
            views=views_by_sample_id.get(tick.sample_id, []),
            tag_names=tag_names_by_sample_id.get(tick.sample_id, []),
        )
        for tick in ticks
    ]


def _load_ticks(session: Session, sequence_id: UUID) -> list[_Tick]:
    """Loads every tick of a sequence, in `seq_number` order.

    Raises:
        ExportError: If a tick has no timestamp.
    """
    links = sequence_resolver.get_sample_links(session=session, sequence_sample_id=sequence_id)
    point_cloud_mcaps_by_sample_id = mcap_resolver.get_point_cloud_mcaps_by_group_sample_ids(
        session=session, group_sample_ids=[link.sample_id for link in links]
    )
    ticks: list[_Tick] = []
    for link in links:
        if link.timestamp_ns is None:
            raise ExportError(
                f"Sequence {sequence_id} has no timestamp at seq_number {link.seq_number}."
            )
        log_time_ns = _log_time_ns(
            point_cloud_mcaps=point_cloud_mcaps_by_sample_id.get(link.sample_id, []),
            sweep_timestamp_ns=link.timestamp_ns,
        )
        ticks.append(
            _Tick(sample_id=link.sample_id, timestamp_ns=link.timestamp_ns, log_time_ns=log_time_ns)
        )
    return ticks


def _load_cuboid_views(
    session: Session, sample_ids: Sequence[UUID], annotation_collection_id: UUID
) -> dict[UUID, list[AnnotationView]]:
    """Loads the cuboids of the ticks from the chosen annotation source.

    Returns:
        The cuboids of each tick, keyed by the tick's group sample ID. A tick without
        cuboids is not in the result.

    Raises:
        ExportError: If a cuboid has an empty `frame_id` or no track.
    """
    annotations = annotation_resolver.get_all_by_parent_sample_ids_and_annotation_collection_id(
        session=session,
        parent_sample_ids=sample_ids,
        annotation_collection_id=annotation_collection_id,
        annotation_types=[AnnotationType.CUBOID_3D],
        load_view_relationships=True,
    )
    views = [
        AnnotationView.from_annotation_table(annotation=annotation) for annotation in annotations
    ]
    _validate_cuboid_annotations(views=views)
    views_by_sample_id: dict[UUID, list[AnnotationView]] = {}
    for view in views:
        views_by_sample_id.setdefault(view.parent_sample_id, []).append(view)
    return views_by_sample_id


def _validate_cuboid_annotations(views: Sequence[AnnotationView]) -> None:
    """Checks that every cuboid has a frame and a track before it is mapped.

    Raises:
        ExportError: If a cuboid has an empty `frame_id` or no track.
    """
    for view in views:
        cuboid = view.cuboid_3d_details
        if cuboid is None:
            continue
        if not cuboid.frame_id:
            raise ExportError(f"Annotation {view.sample_id} has no frame_id.")
        if view.object_track_number is None:
            raise ExportError(f"Annotation {view.sample_id} has no object track.")


def _map_to_target_frame(
    session: Session,
    recording: RecordingTable,
    ticks: Sequence[_Tick],
    views_by_sample_id: Mapping[UUID, list[AnnotationView]],
    target_frame_id: str,
) -> dict[UUID, list[AnnotationView]]:
    """Maps the cuboids of every tick into `target_frame_id`.

    The transforms are loaded and the recording is opened only if a cuboid must be
    mapped.

    Raises:
        ExportError: If the recording cannot be read, or no chain of transforms
            connects a cuboid's frame to `target_frame_id`.
    """
    mapped = dict(views_by_sample_id)
    ticks_to_map = [
        tick
        for tick in ticks
        if cuboids_in_frame.source_frame_ids(
            annotations=views_by_sample_id.get(tick.sample_id, []), target_frame_id=target_frame_id
        )
    ]
    if not ticks_to_map:
        return mapped
    transforms = _load_transforms(session=session, recording=recording, ticks=ticks_to_map)
    try:
        with reader_cache.borrow_reader(uri=transforms.uri) as reader:
            for tick in ticks_to_map:
                mapped[tick.sample_id] = _map_tick(
                    reader=reader,
                    tick=tick,
                    views=views_by_sample_id[tick.sample_id],
                    target_frame_id=target_frame_id,
                    transforms=transforms,
                )
    except (OSError, McapError, McapAccessError) as error:
        raise ExportError(f"Cannot read recording {transforms.uri}: {error}") from error
    return mapped


def _load_transforms(
    session: Session, recording: RecordingTable, ticks: Sequence[_Tick]
) -> _RecordingTransforms:
    """Loads the transforms of a recording that the ticks need, once for all ticks."""
    window_ns = calibration.DYNAMIC_TRANSFORM_WINDOW_NS
    timestamps_ns = [tick.timestamp_ns for tick in ticks]
    dynamic_transforms = load_dynamic_transforms.load_dynamic_transforms_between(
        session=session,
        recording_id=recording.recording_id,
        start_ns=max(min(timestamps_ns) - window_ns, 0),
        end_ns=max(timestamps_ns) + window_ns,
    )
    return _RecordingTransforms(
        uri=recording.uri,
        static_transforms=load_static_transforms.load_static_transforms(
            session=session, recording_id=recording.recording_id
        ),
        dynamic_transforms=None
        if dynamic_transforms is None
        else DynamicTransformsByTime(edges=dynamic_transforms),
    )


def _map_tick(
    reader: McapFileReader,
    tick: _Tick,
    views: Sequence[AnnotationView],
    target_frame_id: str,
    transforms: _RecordingTransforms,
) -> list[AnnotationView]:
    """Maps the cuboids of one tick into `target_frame_id`.

    Raises:
        ExportError: If no chain of transforms connects a cuboid's frame to
            `target_frame_id`.
    """
    dynamic_transforms = (
        None
        if transforms.dynamic_transforms is None
        else transforms.dynamic_transforms.near(timestamp_ns=tick.timestamp_ns)
    )
    try:
        return cuboids_in_frame.map_cuboids(
            reader=reader,
            annotations=views,
            target_frame_id=target_frame_id,
            timestamp_ns=tick.timestamp_ns,
            static_transforms=transforms.static_transforms,
            dynamic_transforms=dynamic_transforms,
        )
    except (McapAccessError, TransformNotFoundError) as error:
        source_frame_ids = sorted(
            cuboids_in_frame.source_frame_ids(annotations=views, target_frame_id=target_frame_id)
        )
        raise ExportError(
            f"Recording {transforms.uri}: cannot map cuboids from frames {source_frame_ids} "
            f"to frame '{target_frame_id}' at timestamp {tick.timestamp_ns}: {error}"
        ) from error


def _tick_message(
    tick: _Tick, views: Sequence[AnnotationView], tag_names: Sequence[str]
) -> tuple[int, SceneUpdateLabels]:
    """Builds the log time and the SceneUpdate labels of one tick.

    The cuboids are sorted by track id, class name and annotation ID, so the message
    order does not depend on the database order.
    """
    labels_and_ids = [
        (_to_cuboid_label(view=view, sweep_timestamp_ns=tick.timestamp_ns), view.sample_id)
        for view in views
    ]
    labels_and_ids.sort(key=lambda pair: (pair[0].track_id, pair[0].class_name, pair[1]))
    labels = SceneUpdateLabels(
        cuboids=tuple(label for label, _ in labels_and_ids),
        frame_tags=_frame_tags(tag_names=tag_names, sweep_timestamp_ns=tick.timestamp_ns),
    )
    return tick.log_time_ns, labels


def _to_cuboid_label(view: AnnotationView, sweep_timestamp_ns: int) -> CuboidLabel:
    """Converts one mapped cuboid annotation to a `CuboidLabel`."""
    cuboid = view.cuboid_3d_details
    assert cuboid is not None  # Only CUBOID_3D annotations are loaded.
    assert view.object_track_number is not None  # Checked by `_validate_cuboid_annotations`.
    return CuboidLabel(
        timestamp_ns=sweep_timestamp_ns,
        frame_id=cuboid.frame_id,
        class_name=view.annotation_label.annotation_label_name,
        track_id=view.object_track_number,
        parent_track_id=view.parent_object_track_number,
        interpolated=cuboid.interpolated,
        position=(cuboid.px, cuboid.py, cuboid.pz),
        rotation=(cuboid.qx, cuboid.qy, cuboid.qz, cuboid.qw),
        size=(cuboid.sx, cuboid.sy, cuboid.sz),
    )


def _frame_tags(tag_names: Sequence[str], sweep_timestamp_ns: int) -> FrameTags | None:
    """Returns the tag names of the tick group as `FrameTags`, or `None` if it has none."""
    if not tag_names:
        return None
    return FrameTags(timestamp_ns=sweep_timestamp_ns, tags=tuple(tag_names), note=None)


def _log_time_ns(point_cloud_mcaps: Sequence[McapTable], sweep_timestamp_ns: int) -> int:
    """Returns the log time of the point cloud channel captured at the sweep time.

    Falls back to the sweep timestamp if no point cloud channel matches it. If several
    channels match, the one with the lowest `channel_id` wins.

    Args:
        point_cloud_mcaps: The point cloud locators of the tick, ordered by
            `channel_id`.
        sweep_timestamp_ns: The sweep timestamp of the tick.
    """
    for mcap in point_cloud_mcaps:
        if mcap.capture_timestamp_ns == sweep_timestamp_ns:
            return mcap.log_time_ns
    return sweep_timestamp_ns
