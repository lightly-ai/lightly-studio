"""Service functions for the per-tick details of an MCAP sequence."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from uuid import UUID

import numpy as np
from numpy.typing import NDArray
from sqlmodel import Session

from lightly_studio.core.mcap import transforms
from lightly_studio.core.mcap.errors import McapAccessError
from lightly_studio.models.annotation.annotation_base import AnnotationView
from lightly_studio.models.mcap_group_component_definition import McapDataType
from lightly_studio.models.mcap_sequence_ticks import TickChannelView, TickDetailView
from lightly_studio.resolvers import (
    annotation_resolver,
    collection_resolver,
    mcap_group_sequence_resolver,
    mcap_resolver,
    recording_resolver,
    sample_resolver,
    sequence_resolver,
)
from lightly_studio.services.recording_service import (
    load_static_transforms,
    reader_cache,
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
    hold the MCAP locators for every channel of that tick and the annotations
    attached to the tick group.

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
    mcap_sequence = mcap_group_sequence_resolver.get_by_id(session=session, sample_id=sequence_id)
    if mcap_sequence is None:
        return None
    sample = sample_resolver.get_by_id(session=session, sample_id=sequence_id)
    if sample is None:
        return None
    collection = collection_resolver.get_by_id(session=session, collection_id=sample.collection_id)
    if collection is None or collection.dataset_id != dataset_id:
        return None

    link = sequence_resolver.get_sample_link(
        session=session, sequence_sample_id=sequence_id, seq_number=seq_number
    )
    if link is None:
        return None

    channel_mcaps = mcap_resolver.get_tick_channels(session=session, group_sample_id=link.sample_id)
    camera_channels: dict[str, TickChannelView] = {}
    lidar_channels: dict[str, TickChannelView] = {}
    for name, (mcap, data_type) in channel_mcaps.items():
        channel = TickChannelView.from_mcap_table(mcap=mcap, group_component_name=name)
        if data_type is McapDataType.POINT_CLOUD:
            lidar_channels[name] = channel
        elif data_type is McapDataType.VIDEO_FRAME:
            camera_channels[name] = channel
    annotations = [
        AnnotationView.from_annotation_table(annotation=annotation)
        for annotation in annotation_resolver.get_all_by_parent_sample_ids(
            session=session, parent_sample_ids=[link.sample_id]
        )
    ]
    if target_frame_id is not None:
        annotations = _cuboids_in_frame(
            session=session,
            recording_id=mcap_sequence.recording_id,
            annotations=annotations,
            target_frame_id=target_frame_id,
            timestamp_ns=link.timestamp_ns,
        )
    return TickDetailView(
        recording_id=mcap_sequence.recording_id,
        seq_number=link.seq_number,
        timestamp_ns=link.timestamp_ns,
        camera_channels=camera_channels,
        lidar_channels=lidar_channels,
        annotations=annotations,
    )


def _cuboids_in_frame(
    session: Session,
    recording_id: UUID,
    annotations: Sequence[AnnotationView],
    target_frame_id: str,
    timestamp_ns: int | None,
) -> list[AnnotationView]:
    """Maps the 3D cuboids of a tick to a target frame.

    Other annotations and cuboids that are already in the target frame stay unchanged.
    The recording and its static transforms are only read if a cuboid must be mapped.
    The tick timestamp is a capture time, so the dynamic transforms are matched by
    their capture time too.

    Raises:
        McapAccessError: If a cuboid must be mapped but the tick has no timestamp or
            the recording does not exist, or no chain of transforms connects the frames.
    """
    source_frame_ids = {
        annotation.cuboid_3d_details.frame_id
        for annotation in annotations
        if annotation.cuboid_3d_details is not None
    } - {target_frame_id}
    if not source_frame_ids:
        return list(annotations)
    if timestamp_ns is None:
        raise McapAccessError(
            f"The tick has no timestamp, so its cuboids in frames {sorted(source_frame_ids)} "
            f"cannot be mapped to frame '{target_frame_id}'."
        )
    recording = recording_resolver.get_by_id(session=session, recording_id=recording_id)
    if recording is None:
        raise McapAccessError(f"Recording {recording_id} was not found.")
    reader = reader_cache.get_cached_reader(uri=recording.uri)
    static_transforms = load_static_transforms.load_static_transforms(
        session=session, recording_id=recording_id
    )
    matrix_by_frame_id = {
        frame_id: transform_to_target_frame.transform_to_target_frame(
            reader=reader,
            source_frame_id=frame_id,
            target_frame_id=target_frame_id,
            timestamp_ns=timestamp_ns,
            static_transforms=static_transforms,
        )
        for frame_id in source_frame_ids
    }
    return [
        _cuboid_in_frame(
            annotation=annotation,
            matrix_by_frame_id=matrix_by_frame_id,
            target_frame_id=target_frame_id,
        )
        for annotation in annotations
    ]


def _cuboid_in_frame(
    annotation: AnnotationView,
    matrix_by_frame_id: Mapping[str, NDArray[np.float64] | None],
    target_frame_id: str,
) -> AnnotationView:
    """Maps the cuboid of an annotation with the transform of its frame.

    An annotation without a cuboid, or with a cuboid that has no transform because it
    is already in the target frame, stays unchanged.
    """
    cuboid = annotation.cuboid_3d_details
    matrix = None if cuboid is None else matrix_by_frame_id.get(cuboid.frame_id)
    if cuboid is None or matrix is None:
        return annotation
    (px, py, pz), (qx, qy, qz, qw) = transforms.transform_pose(
        matrix=matrix,
        position=(cuboid.px, cuboid.py, cuboid.pz),
        rotation=(cuboid.qx, cuboid.qy, cuboid.qz, cuboid.qw),
    )
    mapped_cuboid = cuboid.model_copy(
        update={
            "frame_id": target_frame_id,
            "px": px,
            "py": py,
            "pz": pz,
            "qx": qx,
            "qy": qy,
            "qz": qz,
            "qw": qw,
        }
    )
    return annotation.model_copy(update={"cuboid_3d_details": mapped_cuboid})
