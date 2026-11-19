"""Interpolate the cuboids of an object track between its manual cuboids."""

from __future__ import annotations

import bisect
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from sqlmodel import Session

from lightly_studio.core.mcap.errors import TransformNotFoundError
from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationCreate,
    AnnotationType,
)
from lightly_studio.models.annotation.cuboid_3d import Cuboid3DAnnotationTable, Cuboid3DCreate
from lightly_studio.models.annotation.cuboid_interpolation import CuboidInterpolationRange
from lightly_studio.models.annotation.object_track import ObjectTrackTable
from lightly_studio.models.sequence import SampleSequenceLinkTable
from lightly_studio.resolvers import (
    annotation_resolver,
    collection_resolver,
    evaluation_run_resolver,
    sequence_resolver,
)
from lightly_studio.services.object_track_service import pose_interpolation
from lightly_studio.services.object_track_service.pose_interpolation import CuboidPose, TickPosition
from lightly_studio.services.recording_service import world_poses
from lightly_studio.services.recording_service.world_poses import Pose, WorldPoses


@dataclass
class _TrackCuboid:
    annotation: AnnotationBaseTable
    details: Cuboid3DAnnotationTable
    seq_number: int


@dataclass(frozen=True)
class _WorldFrame:
    """Maps cuboid poses to and from a world frame."""

    world: WorldPoses
    world_frame_id: str

    def to_world(self, pose: CuboidPose, frame_id: str, timestamp_ns: int) -> CuboidPose:
        return self._map(
            pose=pose,
            source_frame_id=frame_id,
            target_frame_id=self.world_frame_id,
            timestamp_ns=timestamp_ns,
        )

    def from_world(self, pose: CuboidPose, frame_id: str, timestamp_ns: int) -> CuboidPose:
        return self._map(
            pose=pose,
            source_frame_id=self.world_frame_id,
            target_frame_id=frame_id,
            timestamp_ns=timestamp_ns,
        )

    def _map(
        self, pose: CuboidPose, source_frame_id: str, target_frame_id: str, timestamp_ns: int
    ) -> CuboidPose:
        mapped = self.world.map_pose(
            pose=Pose(position=pose.center, rotation=pose.rotation),
            source_frame_id=source_frame_id,
            target_frame_id=target_frame_id,
            timestamp_ns=timestamp_ns,
        )
        return CuboidPose(center=mapped.position, size=pose.size, rotation=mapped.rotation)


def interpolate_cuboids(
    session: Session,
    object_track: ObjectTrackTable,
    interpolation_range: CuboidInterpolationRange,
) -> None:
    """Interpolate the ticks of a range between consecutive manual cuboids of a track.

    Only the cuboids of the range's sequence and annotation source are used. Interpolated
    cuboids on the range's ticks are replaced. With stored transforms, a pair is
    interpolated in the world frame, so cuboids in a moving frame follow that frame.
    Pairs with different classes, or frames that cannot be mapped, are skipped.

    Raises:
        ValueError: If the range starts after it ends.
    """
    if interpolation_range.start_seq_number > interpolation_range.end_seq_number:
        raise ValueError("start_seq_number must not be greater than end_seq_number.")
    cuboids = _load_track_cuboids(
        session=session,
        object_track_id=object_track.object_track_id,
        interpolation_range=interpolation_range,
    )
    ticks = sequence_resolver.get_sample_links(
        session=session, sequence_sample_id=interpolation_range.sequence_id
    )
    creates, replaced_ids = _plan(
        cuboids=cuboids,
        ticks=ticks,
        world=_load_world(
            session=session,
            sequence_sample_id=interpolation_range.sequence_id,
            ticks=_affected_ticks(
                cuboids=cuboids, ticks=ticks, interpolation_range=interpolation_range
            ),
        ),
        interpolation_range=interpolation_range,
    )
    if creates:
        _create(
            session=session,
            annotation_source_id=interpolation_range.annotation_source_id,
            creates=creates,
        )
    if replaced_ids:
        annotation_resolver.delete_annotations_by_ids(session=session, annotation_ids=replaced_ids)


def _load_track_cuboids(
    session: Session, object_track_id: UUID, interpolation_range: CuboidInterpolationRange
) -> list[_TrackCuboid]:
    """Return the track's cuboids of the range's sequence and source, ordered by tick."""
    annotations = [
        annotation
        for annotation in annotation_resolver.get_cuboids_by_object_track_ids(
            session=session, object_track_ids=[object_track_id]
        )
        if annotation.annotation_collection_id == interpolation_range.annotation_source_id
    ]
    links = sequence_resolver.get_links_by_sample_ids(
        session=session, sample_ids={a.parent_sample_id for a in annotations}
    )
    cuboids = []
    for annotation in annotations:
        link = links.get(annotation.parent_sample_id)
        details = annotation.cuboid_3d_details
        if link is None or details is None:
            continue
        if link.sequence_sample_id != interpolation_range.sequence_id:
            continue
        cuboids.append(
            _TrackCuboid(annotation=annotation, details=details, seq_number=link.seq_number)
        )
    return sorted(cuboids, key=lambda cuboid: cuboid.seq_number)


def _affected_ticks(
    cuboids: Sequence[_TrackCuboid],
    ticks: Sequence[SampleSequenceLinkTable],
    interpolation_range: CuboidInterpolationRange,
) -> list[SampleSequenceLinkTable]:
    """Return the ticks from the manual cuboid before the range to the one after it."""
    anchor_seq_numbers = [
        cuboid.seq_number for cuboid in cuboids if not cuboid.details.interpolated
    ]
    first = max(
        (n for n in anchor_seq_numbers if n <= interpolation_range.start_seq_number),
        default=interpolation_range.start_seq_number,
    )
    last = min(
        (n for n in anchor_seq_numbers if n >= interpolation_range.end_seq_number),
        default=interpolation_range.end_seq_number,
    )
    return [tick for tick in ticks if first <= tick.seq_number <= last]


def _load_world(
    session: Session, sequence_sample_id: UUID, ticks: Sequence[SampleSequenceLinkTable]
) -> WorldPoses | None:
    timestamps = [tick.timestamp_ns for tick in ticks if tick.timestamp_ns is not None]
    if not timestamps:
        return None
    return world_poses.load_world_poses(
        session=session,
        sequence_id=sequence_sample_id,
        start_ns=min(timestamps),
        end_ns=max(timestamps),
    )


def _plan(
    cuboids: Sequence[_TrackCuboid],
    ticks: Sequence[SampleSequenceLinkTable],
    world: WorldPoses | None,
    interpolation_range: CuboidInterpolationRange,
) -> tuple[list[AnnotationCreate], list[UUID]]:
    """Return the cuboids to create and the IDs of the interpolated cuboids they replace."""

    def in_range(seq_number: int) -> bool:
        return (
            interpolation_range.start_seq_number <= seq_number <= interpolation_range.end_seq_number
        )

    anchors = [cuboid for cuboid in cuboids if not cuboid.details.interpolated]
    interpolated = [cuboid for cuboid in cuboids if cuboid.details.interpolated]
    seq_numbers = [tick.seq_number for tick in ticks]
    anchor_seq_numbers = {anchor.seq_number for anchor in anchors}
    creates: list[AnnotationCreate] = []
    # A new manual cuboid replaces the interpolated cuboid on its tick.
    replaced_ids = [
        cuboid.annotation.sample_id
        for cuboid in interpolated
        if cuboid.seq_number in anchor_seq_numbers and in_range(cuboid.seq_number)
    ]
    for start, end in zip(anchors, anchors[1:]):
        first = bisect.bisect_left(seq_numbers, start.seq_number)
        last = bisect.bisect_right(seq_numbers, end.seq_number)
        pair_ticks = ticks[first:last]
        if not any(in_range(tick.seq_number) for tick in pair_ticks[1:-1]):
            continue
        gap_creates = _interpolate_pair(start=start, end=end, pair_ticks=pair_ticks, world=world)
        if gap_creates is None:
            continue
        creates.extend(create for seq_number, create in gap_creates if in_range(seq_number))
        replaced_ids.extend(
            cuboid.annotation.sample_id
            for cuboid in interpolated
            if start.seq_number < cuboid.seq_number < end.seq_number and in_range(cuboid.seq_number)
        )
    return creates, replaced_ids


def _interpolate_pair(
    start: _TrackCuboid,
    end: _TrackCuboid,
    pair_ticks: Sequence[SampleSequenceLinkTable],
    world: WorldPoses | None,
) -> list[tuple[int, AnnotationCreate]] | None:
    """Return the tick number and cuboid for each tick between two anchors, or None to skip."""
    if start.annotation.annotation_label_id != end.annotation.annotation_label_id:
        return None
    world_frame = _world_frame(start=start, end=end, pair_ticks=pair_ticks, world=world)
    if world_frame is not None:
        try:
            return _gap_creates(
                start=start, end=end, pair_ticks=pair_ticks, world_frame=world_frame
            )
        except TransformNotFoundError:
            # Without transforms, fall back to the anchor frame.
            pass
    if start.details.frame_id != end.details.frame_id:
        return None
    return _gap_creates(start=start, end=end, pair_ticks=pair_ticks, world_frame=None)


def _world_frame(
    start: _TrackCuboid,
    end: _TrackCuboid,
    pair_ticks: Sequence[SampleSequenceLinkTable],
    world: WorldPoses | None,
) -> _WorldFrame | None:
    """Return the world frame for a pair, or None to interpolate in the anchor frame."""
    if world is None or any(tick.timestamp_ns is None for tick in pair_ticks):
        return None
    world_frame_id = world.world_frame_of(start.details.frame_id)
    if world_frame_id is None or world_frame_id != world.world_frame_of(end.details.frame_id):
        return None
    if world_frame_id == start.details.frame_id == end.details.frame_id:
        return None
    return _WorldFrame(world=world, world_frame_id=world_frame_id)


def _gap_creates(
    start: _TrackCuboid,
    end: _TrackCuboid,
    pair_ticks: Sequence[SampleSequenceLinkTable],
    world_frame: _WorldFrame | None,
) -> list[tuple[int, AnnotationCreate]]:
    alphas = pose_interpolation.gap_alphas(
        ticks=[
            TickPosition(seq_number=tick.seq_number, timestamp_ns=tick.timestamp_ns)
            for tick in pair_ticks
        ]
    )
    frame_id = start.details.frame_id
    start_pose = _pose(details=start.details)
    end_pose = _pose(details=end.details)
    if world_frame is not None:
        start_pose = world_frame.to_world(
            pose=start_pose, frame_id=frame_id, timestamp_ns=_timestamp(pair_ticks[0])
        )
        end_pose = world_frame.to_world(
            pose=end_pose, frame_id=end.details.frame_id, timestamp_ns=_timestamp(pair_ticks[-1])
        )
    creates = []
    for tick, alpha in zip(pair_ticks[1:-1], alphas):
        pose = pose_interpolation.interpolate_pose(start=start_pose, end=end_pose, alpha=alpha)
        if world_frame is not None:
            pose = world_frame.from_world(
                pose=pose, frame_id=frame_id, timestamp_ns=_timestamp(tick)
            )
        creates.append(
            (tick.seq_number, _gap_create(start=start, pose=pose, tick_id=tick.sample_id))
        )
    return creates


def _timestamp(tick: SampleSequenceLinkTable) -> int:
    if tick.timestamp_ns is None:
        raise RuntimeError("Expected `tick.timestamp_ns` to be set.")
    return tick.timestamp_ns


def _gap_create(start: _TrackCuboid, pose: CuboidPose, tick_id: UUID) -> AnnotationCreate:
    px, py, pz = pose.center
    sx, sy, sz = pose.size
    qx, qy, qz, qw = pose.rotation
    return AnnotationCreate(
        annotation_label_id=start.annotation.annotation_label_id,
        annotation_type=AnnotationType.CUBOID_3D,
        parent_sample_id=tick_id,
        object_track_id=start.annotation.object_track_id,
        cuboid_3d=Cuboid3DCreate(
            frame_id=start.details.frame_id,
            px=px,
            py=py,
            pz=pz,
            qx=qx,
            qy=qy,
            qz=qz,
            qw=qw,
            sx=sx,
            sy=sy,
            sz=sz,
            interpolated=True,
        ),
    )


def _pose(details: Cuboid3DAnnotationTable) -> CuboidPose:
    return CuboidPose(
        center=(details.px, details.py, details.pz),
        size=(details.sx, details.sy, details.sz),
        rotation=(details.qx, details.qy, details.qz, details.qw),
    )


def _create(session: Session, annotation_source_id: UUID, creates: list[AnnotationCreate]) -> None:
    source = collection_resolver.get_by_id(session=session, collection_id=annotation_source_id)
    if source is None:
        raise RuntimeError("Expected `source` to be set.")
    if source.parent_collection_id is None:
        raise RuntimeError("Expected `source.parent_collection_id` to be set.")
    annotation_resolver.create_many(
        session=session,
        parent_collection_id=source.parent_collection_id,
        annotations=creates,
        collection_name=source.name,
    )
    evaluation_run_resolver.mark_stale_by_collection_id(
        session=session, collection_id=annotation_source_id
    )
