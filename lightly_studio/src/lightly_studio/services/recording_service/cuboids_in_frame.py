"""Maps the 3D cuboids of a tick to a target coordinate frame."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from uuid import UUID

import numpy as np
from numpy.typing import NDArray
from sqlmodel import Session

from lightly_studio.core.mcap import transforms
from lightly_studio.core.mcap.errors import McapAccessError
from lightly_studio.models.annotation.annotation_base import AnnotationView
from lightly_studio.resolvers import recording_resolver
from lightly_studio.services.recording_service import (
    load_dynamic_transforms,
    load_static_transforms,
    reader_cache,
    transform_to_target_frame,
)


def cuboids_in_frame(
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

    Args:
        session: The database session.
        recording_id: The recording of the tick.
        annotations: The annotations of the tick.
        target_frame_id: The coordinate frame to map the cuboids to.
        timestamp_ns: The capture time of the tick in nanoseconds, or `None` if the
            tick has no timestamp.

    Returns:
        The annotations in the order of `annotations`, with each cuboid in
        `target_frame_id`.

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
    static_transforms = load_static_transforms.load_static_transforms(
        session=session, recording_id=recording_id
    )
    dynamic_transforms = load_dynamic_transforms.load_dynamic_transforms_near(
        session=session, recording_id=recording_id, timestamp_ns=timestamp_ns
    )
    with reader_cache.borrow_reader(uri=recording.uri) as reader:
        matrix_by_frame_id = {
            frame_id: transform_to_target_frame.transform_to_target_frame(
                reader=reader,
                source_frame_id=frame_id,
                target_frame_id=target_frame_id,
                timestamp_ns=timestamp_ns,
                static_transforms=static_transforms,
                dynamic_transforms=dynamic_transforms,
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
