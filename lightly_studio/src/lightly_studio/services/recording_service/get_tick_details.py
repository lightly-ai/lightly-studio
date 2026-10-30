"""Service functions for the per-tick details of an MCAP sequence."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from uuid import UUID

import numpy as np
from numpy.typing import NDArray
from sqlmodel import Session

from lightly_studio.core.mcap.errors import McapAccessError, TransformNotFoundError
from lightly_studio.core.mcap.reader import McapFileReader
from lightly_studio.core.mcap.type_definitions import StaticTransform
from lightly_studio.models.annotation.annotation_base import AnnotationView
from lightly_studio.models.mcap_group_component_definition import McapDataType
from lightly_studio.models.mcap_sequence_ticks import (
    CameraProjectionView,
    TickChannelView,
    TickDetailView,
)
from lightly_studio.models.tag import TagView
from lightly_studio.resolvers import (
    annotation_resolver,
    mcap_group_sequence_resolver,
    recording_resolver,
    sample_resolver,
    sensor_calibration_resolver,
)
from lightly_studio.services.recording_service import (
    cuboids_in_frame,
    load_dynamic_transforms,
    load_static_transforms,
    reader_cache,
    resolve_tick,
    transform_to_target_frame,
)


def get_tick_details(
    session: Session,
    dataset_id: UUID,
    sequence_id: UUID,
    seq_number: int,
    target_frame_id: str | None = None,
) -> TickDetailView | None:
    """Return the tick details for one tick of a sequence.

    The tick is identified by `sequence_id` and `seq_number`, and the details
    hold the MCAP locators for every channel of that tick, and the annotations
    and tags attached to the tick group.

    Args:
        session: The database session.
        dataset_id: The dataset the sequence must belong to.
        sequence_id: The sequence sample ID.
        seq_number: The zero-based index of the tick to fetch.
        target_frame_id: The coordinate frame to express the 3D cuboids in, e.g. the
            frame the point clouds are shown in. The cuboids are mapped with the static
            and dynamic transforms of the recording at the tick timestamp. The static
            transforms are the edges stored when the recording was indexed. `None` keeps
            each cuboid in its own frame.

    Returns:
        The tick detail, or `None` if the sequence does not exist, does not belong
        to `dataset_id`, or has no tick at `seq_number`.

    Raises:
        McapAccessError: If a cuboid must be mapped to `target_frame_id` but the tick
            has no timestamp, or no chain of transforms connects the frames.
    """
    tick = resolve_tick.resolve_tick(
        session=session, dataset_id=dataset_id, sequence_id=sequence_id, seq_number=seq_number
    )
    if tick is None:
        return None
    link = tick.link

    camera_timestamps = {
        name: mcap.capture_timestamp_ns
        for name, (mcap, data_type) in tick.channels.items()
        if data_type is McapDataType.VIDEO_FRAME
    }
    projections = _camera_projections(
        session=session,
        sequence_id=sequence_id,
        recording_id=tick.recording_id,
        target_frame_id=target_frame_id,
        camera_timestamps=camera_timestamps,
    )
    camera_channels: dict[str, TickChannelView] = {}
    lidar_channels: dict[str, TickChannelView] = {}
    for name, (mcap, data_type) in tick.channels.items():
        channel = TickChannelView.from_mcap_table(mcap=mcap, group_component_name=name)
        if data_type is McapDataType.POINT_CLOUD:
            lidar_channels[name] = channel
        elif data_type is McapDataType.VIDEO_FRAME:
            camera_channels[name] = channel.model_copy(update={"projection": projections.get(name)})
    annotations = [
        AnnotationView.from_annotation_table(annotation=annotation)
        for annotation in annotation_resolver.get_all_by_parent_sample_ids(
            session=session, parent_sample_ids=[link.sample_id]
        )
    ]
    if target_frame_id is not None:
        annotations = cuboids_in_frame.cuboids_in_frame(
            session=session,
            recording_id=tick.recording_id,
            annotations=annotations,
            target_frame_id=target_frame_id,
            timestamp_ns=link.timestamp_ns,
        )
    tick_sample = sample_resolver.get_by_id(session=session, sample_id=link.sample_id)
    assert tick_sample is not None
    return TickDetailView(
        sample_id=link.sample_id,
        collection_id=tick_sample.collection_id,
        recording_id=tick.recording_id,
        seq_number=link.seq_number,
        timestamp_ns=link.timestamp_ns,
        camera_channels=camera_channels,
        lidar_channels=lidar_channels,
        annotations=annotations,
        tags=[TagView.model_validate(tag) for tag in tick_sample.tags],
    )


def _camera_projections(
    session: Session,
    sequence_id: UUID,
    recording_id: UUID,
    target_frame_id: str | None,
    camera_timestamps: Mapping[str, int],
) -> dict[str, CameraProjectionView]:
    """Build projection metadata for cameras in the requested scene frame."""
    if target_frame_id is None or not camera_timestamps:
        return {}

    info = mcap_group_sequence_resolver.get_info(session=session, sample_id=sequence_id)
    if info is None:
        return {}
    calibrations = {
        calibration.collection_id: calibration
        for calibration in sensor_calibration_resolver.get_all_by_recording_id(
            session=session, recording_id=recording_id
        )
    }
    components = [
        component
        for component in info.components
        if component.mcap_data_type is McapDataType.VIDEO_FRAME
        and component.frame_id is not None
        and component.collection_id in calibrations
    ]
    if not components:
        return {}
    recording = recording_resolver.get_by_id(session=session, recording_id=recording_id)
    if recording is None:
        return {}
    static_transforms = load_static_transforms.load_static_transforms(
        session=session, recording_id=recording_id
    )
    projections: dict[str, CameraProjectionView] = {}
    dynamic_transforms_by_timestamp: dict[int, Sequence[StaticTransform] | None] = {}
    with reader_cache.borrow_reader(uri=recording.uri) as reader:
        for component in components:
            calibration = calibrations.get(component.collection_id)
            if calibration is None or component.frame_id is None:
                continue
            projection_timestamp_ns = camera_timestamps.get(component.group_component_name)
            if projection_timestamp_ns is None:
                continue
            if projection_timestamp_ns not in dynamic_transforms_by_timestamp:
                dynamic_transforms_by_timestamp[projection_timestamp_ns] = (
                    load_dynamic_transforms.load_dynamic_transforms_near(
                        session=session,
                        recording_id=recording_id,
                        timestamp_ns=projection_timestamp_ns,
                    )
                )
            matrix = _get_camera_projection_matrix(
                reader=reader,
                source_frame_id=target_frame_id,
                target_frame_id=component.frame_id,
                timestamp_ns=projection_timestamp_ns,
                static_transforms=static_transforms,
                dynamic_transforms=dynamic_transforms_by_timestamp[projection_timestamp_ns],
            )
            if matrix is None:
                continue
            projections[component.group_component_name] = CameraProjectionView(
                width=calibration.width,
                height=calibration.height,
                camera_matrix=calibration.k,
                scene_to_camera=[float(value) for value in matrix.reshape(-1)],
            )
    return projections


def _get_camera_projection_matrix(  # noqa: PLR0913
    reader: McapFileReader,
    source_frame_id: str,
    target_frame_id: str,
    timestamp_ns: int,
    static_transforms: Sequence[StaticTransform],
    dynamic_transforms: Sequence[StaticTransform] | None,
) -> NDArray[np.float64] | None:
    """Resolve the scene-to-camera transform, skipping unavailable transforms."""
    if source_frame_id == target_frame_id:
        return np.eye(4, dtype=np.float64)
    try:
        return transform_to_target_frame.transform_to_target_frame(
            reader=reader,
            source_frame_id=source_frame_id,
            target_frame_id=target_frame_id,
            timestamp_ns=timestamp_ns,
            static_transforms=static_transforms,
            dynamic_transforms=dynamic_transforms,
        )
    except (McapAccessError, TransformNotFoundError):
        return None
