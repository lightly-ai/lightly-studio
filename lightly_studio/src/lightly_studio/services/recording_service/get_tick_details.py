"""Service functions for the per-tick details of an MCAP sequence."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
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
from lightly_studio.models.sensor_calibration import SensorCalibrationTable
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


@dataclass(frozen=True)
class _CalibratedCamera:
    """A camera of a tick that can be projected into the scene frame."""

    group_component_name: str
    frame_id: str
    timestamp_ns: int
    calibration: SensorCalibrationTable


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

    annotations = [
        AnnotationView.from_annotation_table(annotation=annotation)
        for annotation in annotation_resolver.get_all_by_parent_sample_ids(
            session=session, parent_sample_ids=[link.sample_id], load_view_relationships=True
        )
    ]
    projections: dict[str, CameraProjectionView] = {}
    if target_frame_id is not None:
        cameras = _calibrated_cameras(
            session=session,
            sequence_id=sequence_id,
            recording_id=tick.recording_id,
            camera_timestamps={
                name: mcap.capture_timestamp_ns
                for name, (mcap, data_type) in tick.channels.items()
                if data_type is McapDataType.VIDEO_FRAME
            },
        )
        projections, annotations = _in_target_frame(
            session=session,
            recording_id=tick.recording_id,
            target_frame_id=target_frame_id,
            timestamp_ns=link.timestamp_ns,
            cameras=cameras,
            annotations=annotations,
        )
    camera_channels: dict[str, TickChannelView] = {}
    lidar_channels: dict[str, TickChannelView] = {}
    for name, (mcap, data_type) in tick.channels.items():
        channel = TickChannelView.from_mcap_table(mcap=mcap, group_component_name=name)
        if data_type is McapDataType.POINT_CLOUD:
            lidar_channels[name] = channel
        elif data_type is McapDataType.VIDEO_FRAME:
            camera_channels[name] = channel.model_copy(update={"projection": projections.get(name)})
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


def _calibrated_cameras(
    session: Session,
    sequence_id: UUID,
    recording_id: UUID,
    camera_timestamps: Mapping[str, int],
) -> list[_CalibratedCamera]:
    """Returns the cameras of a tick that have a frame, a calibration and a timestamp."""
    if not camera_timestamps:
        return []
    info = mcap_group_sequence_resolver.get_info(session=session, sample_id=sequence_id)
    if info is None:
        return []
    calibrations = {
        row.collection_id: row
        for row in sensor_calibration_resolver.get_all_by_recording_id(
            session=session, recording_id=recording_id
        )
    }
    cameras = []
    for component in info.components:
        timestamp_ns = camera_timestamps.get(component.group_component_name)
        camera_calibration = calibrations.get(component.collection_id)
        if (
            component.mcap_data_type is not McapDataType.VIDEO_FRAME
            or component.frame_id is None
            or camera_calibration is None
            or timestamp_ns is None
        ):
            continue
        cameras.append(
            _CalibratedCamera(
                group_component_name=component.group_component_name,
                frame_id=component.frame_id,
                timestamp_ns=timestamp_ns,
                calibration=camera_calibration,
            )
        )
    return cameras


def _in_target_frame(  # noqa: PLR0913
    session: Session,
    recording_id: UUID,
    target_frame_id: str,
    timestamp_ns: int | None,
    cameras: Sequence[_CalibratedCamera],
    annotations: Sequence[AnnotationView],
) -> tuple[dict[str, CameraProjectionView], list[AnnotationView]]:
    """Builds the camera projections and maps the cuboids to the target frame.

    The recording, its static transforms and its dynamic transforms near every
    timestamp of the tick are read once, and one reader serves all lookups. A camera
    without a transform to the target frame gets no projection.

    Raises:
        McapAccessError: If a cuboid must be mapped but the tick has no timestamp or
            the recording does not exist.
        TransformNotFoundError: If no chain of transforms connects a cuboid frame to
            the target frame.
    """
    cuboid_frame_ids = cuboids_in_frame.source_frame_ids(
        annotations=annotations, target_frame_id=target_frame_id
    )
    if cuboid_frame_ids and timestamp_ns is None:
        raise McapAccessError(
            f"The tick has no timestamp, so its cuboids in frames {sorted(cuboid_frame_ids)} "
            f"cannot be mapped to frame '{target_frame_id}'."
        )
    if not cameras and not cuboid_frame_ids:
        return {}, list(annotations)
    recording = recording_resolver.get_by_id(session=session, recording_id=recording_id)
    if recording is None:
        if cuboid_frame_ids:
            raise McapAccessError(f"Recording {recording_id} was not found.")
        return {}, list(annotations)
    cuboid_timestamp_ns = timestamp_ns if cuboid_frame_ids else None
    timestamps_ns = [camera.timestamp_ns for camera in cameras]
    if cuboid_timestamp_ns is not None:
        timestamps_ns.append(cuboid_timestamp_ns)
    static_transforms = load_static_transforms.load_static_transforms(
        session=session, recording_id=recording_id
    )
    dynamic_transforms = load_dynamic_transforms.load_dynamic_transforms_near_times(
        session=session, recording_id=recording_id, timestamps_ns=timestamps_ns
    )
    projections: dict[str, CameraProjectionView] = {}
    with reader_cache.borrow_reader(uri=recording.uri) as reader:
        for camera in cameras:
            matrix = _get_camera_projection_matrix(
                reader=reader,
                source_frame_id=target_frame_id,
                target_frame_id=camera.frame_id,
                timestamp_ns=camera.timestamp_ns,
                static_transforms=static_transforms,
                dynamic_transforms=load_dynamic_transforms.select_near(
                    dynamic_transforms=dynamic_transforms, timestamp_ns=camera.timestamp_ns
                ),
            )
            if matrix is None:
                continue
            projections[camera.group_component_name] = CameraProjectionView(
                width=camera.calibration.width,
                height=camera.calibration.height,
                camera_matrix=camera.calibration.k,
                scene_to_camera=[float(value) for value in matrix.reshape(-1)],
            )
        if cuboid_timestamp_ns is None:
            return projections, list(annotations)
        mapped = cuboids_in_frame.map_cuboids(
            reader=reader,
            annotations=annotations,
            target_frame_id=target_frame_id,
            timestamp_ns=cuboid_timestamp_ns,
            static_transforms=static_transforms,
            dynamic_transforms=load_dynamic_transforms.select_near(
                dynamic_transforms=dynamic_transforms, timestamp_ns=cuboid_timestamp_ns
            ),
        )
    return projections, mapped


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
