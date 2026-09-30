"""Service functions for the per-tick details of an MCAP sequence."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

import numpy as np
from numpy.typing import NDArray
from sqlmodel import Session

from lightly_studio.core.mcap import transforms
from lightly_studio.core.mcap.errors import McapAccessError
from lightly_studio.models.annotation.annotation_base import AnnotationView
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
from lightly_studio.services.recording_service import load_static_transforms, reader_cache


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
        channels={
            name: TickChannelView.from_mcap_table(mcap=mcap, group_component_name=name)
            for name, mcap in channel_mcaps.items()
        },
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
    The recording is only read if a cuboid must be mapped.

    Raises:
        McapAccessError: If a cuboid must be mapped but the tick has no timestamp or
            the recording does not exist, or no chain of transforms connects the frames.
    """
    matrix_by_frame_id: dict[str, NDArray[np.float64]] = {}
    mapped: list[AnnotationView] = []
    for annotation in annotations:
        cuboid = annotation.cuboid_3d_details
        if cuboid is None or cuboid.frame_id == target_frame_id:
            mapped.append(annotation)
            continue
        if cuboid.frame_id not in matrix_by_frame_id:
            matrix_by_frame_id[cuboid.frame_id] = _transform_at(
                session=session,
                recording_id=recording_id,
                parent_frame_id=target_frame_id,
                child_frame_id=cuboid.frame_id,
                timestamp_ns=timestamp_ns,
            )
        (px, py, pz), (qx, qy, qz, qw) = transforms.transform_pose(
            matrix=matrix_by_frame_id[cuboid.frame_id],
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
        mapped.append(annotation.model_copy(update={"cuboid_3d_details": mapped_cuboid}))
    return mapped


def _transform_at(
    session: Session,
    recording_id: UUID,
    parent_frame_id: str,
    child_frame_id: str,
    timestamp_ns: int | None,
) -> NDArray[np.float64]:
    """Returns the transform between two frames of a recording at the tick timestamp.

    Raises:
        McapAccessError: If the tick has no timestamp or the recording does not exist,
            or no chain of transforms connects the frames.
    """
    if timestamp_ns is None:
        raise McapAccessError(
            f"The tick has no timestamp, so its cuboids in frame '{child_frame_id}' cannot "
            f"be mapped to frame '{parent_frame_id}'."
        )
    recording = recording_resolver.get_by_id(session=session, recording_id=recording_id)
    if recording is None:
        raise McapAccessError(f"Recording {recording_id} was not found.")
    reader = reader_cache.get_cached_reader(uri=recording.uri)
    # The tick timestamp is a capture time, and the dynamic transforms are matched by log
    # time. The two differ by the transport delay, which is small compared to the motion
    # of the vehicle between two transforms. The static edges come from the database.
    return reader.get_transform_at(
        parent_frame_id=parent_frame_id,
        child_frame_id=child_frame_id,
        timestamp_ns=timestamp_ns,
        static_transforms=load_static_transforms.load_static_transforms(
            session=session, recording_id=recording_id
        ),
    )
