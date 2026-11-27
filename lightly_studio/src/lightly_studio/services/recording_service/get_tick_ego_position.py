"""Service function for the ego position at one tick of an MCAP sequence."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.core.mcap.errors import McapAccessError, TransformNotFoundError
from lightly_studio.models.mcap_sequence_ticks import EgoPositionFrames, TickEgoPositionView
from lightly_studio.resolvers import recording_resolver
from lightly_studio.services.recording_service import (
    load_dynamic_transforms,
    load_static_transforms,
    reader_cache,
    resolve_tick,
    transform_to_target_frame,
)


def get_tick_ego_position(
    session: Session,
    dataset_id: UUID,
    sequence_id: UUID,
    seq_number: int,
    frames: EgoPositionFrames,
) -> TickEgoPositionView | None:
    """Return the position of the ego frame in the target frame at one tick.

    The position is the origin of `frames.ego_frame_id`, mapped with the static and
    dynamic transforms of the recording at the tick timestamp.

    Args:
        session: The database session.
        dataset_id: The dataset the sequence must belong to.
        sequence_id: The sequence sample ID.
        seq_number: The zero-based index of the tick.
        frames: The frame the scene is shown in, e.g. `map`, and the frame attached to the
            ego, e.g. `CABIN`.

    Returns:
        The ego position, or `None` if the sequence does not exist, does not belong to
        `dataset_id`, or has no tick at `seq_number`. The position in the view is `None` if
        the tick has no timestamp or no chain of transforms connects the frames.
    """
    tick = resolve_tick.resolve_tick(
        session=session, dataset_id=dataset_id, sequence_id=sequence_id, seq_number=seq_number
    )
    if tick is None:
        return None
    if frames.ego_frame_id == frames.target_frame_id:
        return TickEgoPositionView(position=[0.0, 0.0, 0.0])
    timestamp_ns = tick.link.timestamp_ns
    if timestamp_ns is None:
        return TickEgoPositionView(position=None)
    return TickEgoPositionView(
        position=_resolve_ego_position(
            session=session,
            recording_id=tick.recording_id,
            frames=frames,
            timestamp_ns=timestamp_ns,
        )
    )


def _resolve_ego_position(
    session: Session,
    recording_id: UUID,
    frames: EgoPositionFrames,
    timestamp_ns: int,
) -> list[float] | None:
    """Map the origin of the ego frame to the target frame, or `None` if not connected."""
    recording = recording_resolver.get_by_id(session=session, recording_id=recording_id)
    if recording is None:
        return None
    static_transforms = load_static_transforms.load_static_transforms(
        session=session, recording_id=recording_id
    )
    dynamic_transforms = load_dynamic_transforms.load_dynamic_transforms_near(
        session=session, recording_id=recording_id, timestamp_ns=timestamp_ns
    )
    with reader_cache.borrow_reader(uri=recording.uri) as reader:
        try:
            ego_to_target = transform_to_target_frame.transform_to_target_frame(
                reader=reader,
                source_frame_id=frames.ego_frame_id,
                target_frame_id=frames.target_frame_id,
                timestamp_ns=timestamp_ns,
                static_transforms=static_transforms,
                dynamic_transforms=dynamic_transforms,
            )
        # A missing transform is an expected state, e.g. at a gap in `/tf`.
        except (McapAccessError, TransformNotFoundError):
            return None
    if ego_to_target is None:
        raise RuntimeError("Expected a transform between two different frames.")
    return [float(value) for value in ego_to_target[:3, 3]]
