"""Map cuboid poses of a recording through its world frame."""

from __future__ import annotations

import bisect
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from sqlmodel import Session

from lightly_studio.core.mcap import transforms
from lightly_studio.core.mcap.transforms import TransformTree
from lightly_studio.core.mcap.type_definitions import StaticTransform
from lightly_studio.models.mcap_group_sequence import McapGroupSequenceTable
from lightly_studio.services.recording_service.load_dynamic_transforms import (
    load_dynamic_transforms_around,
)
from lightly_studio.services.recording_service.load_static_transforms import (
    load_static_transforms,
)


@dataclass(frozen=True)
class Pose:
    """Position and rotation (quaternion x, y, z, w) in a coordinate frame."""

    position: tuple[float, float, float]
    rotation: tuple[float, float, float, float]


class WorldPoses:
    """Transforms of a recording, to map poses between frames at a capture time.

    The world frame is the root of the transform tree and does not move. For each
    moving frame, the dynamic edge closest to the capture time is used, also if it is
    far from the capture time. A recording can start some time before its first
    dynamic edge, and the cuboids of these ticks must also stand still in the world
    frame.

    Edges with a zero quaternion are not used, because they have no rotation.
    """

    def __init__(
        self,
        static_transforms: Sequence[StaticTransform],
        dynamic_transforms: Sequence[StaticTransform],
    ) -> None:
        """Store the static edges and the dynamic edges of the time range to map."""
        self._static_transforms = _edges_with_rotation(edges=static_transforms)
        valid_dynamic_transforms = _edges_with_rotation(edges=dynamic_transforms)
        self._dynamic_transforms_by_child = _dynamic_transforms_by_child(
            edges=valid_dynamic_transforms
        )
        self._parent_by_child = {
            edge.child_frame_id: edge.parent_frame_id
            for edge in [*self._static_transforms, *valid_dynamic_transforms]
        }

    def world_frame_of(self, frame_id: str) -> str | None:
        """Return the root frame above `frame_id`, or None if no transform names it."""
        if frame_id not in self._parent_by_child and frame_id not in set(
            self._parent_by_child.values()
        ):
            return None
        visited = {frame_id}
        while frame_id in self._parent_by_child:
            frame_id = self._parent_by_child[frame_id]
            if frame_id in visited:
                # A cycle has no root.
                return None
            visited.add(frame_id)
        return frame_id

    def map_pose(
        self, pose: Pose, source_frame_id: str, target_frame_id: str, timestamp_ns: int
    ) -> Pose:
        """Map a pose from `source_frame_id` to `target_frame_id` at a capture time.

        Raises:
            TransformNotFoundError: If the frames are not connected at `timestamp_ns`.
        """
        if source_frame_id == target_frame_id:
            return pose
        closest_dynamic = [
            edges.closest(timestamp_ns=timestamp_ns)
            for edges in self._dynamic_transforms_by_child.values()
        ]
        tree = TransformTree([*self._static_transforms, *closest_dynamic])
        matrix = tree.lookup(target_frame_id=target_frame_id, source_frame_id=source_frame_id)
        position, rotation = transforms.transform_pose(
            matrix=matrix, position=pose.position, rotation=pose.rotation
        )
        return Pose(position=position, rotation=rotation)

    def hold_in_world(self, pose: Pose, frame_id: str, from_ns: int, to_ns: int) -> Pose:
        """Return the pose at `to_ns` of an object that stands still in the world.

        Raises:
            TransformNotFoundError: If the frames are not connected at one of the times.
        """
        world_frame_id = self.world_frame_of(frame_id)
        if world_frame_id is None or world_frame_id == frame_id:
            return pose
        world_pose = self.map_pose(
            pose=pose,
            source_frame_id=frame_id,
            target_frame_id=world_frame_id,
            timestamp_ns=from_ns,
        )
        return self.map_pose(
            pose=world_pose,
            source_frame_id=world_frame_id,
            target_frame_id=frame_id,
            timestamp_ns=to_ns,
        )


class _EdgesOfChild:
    """The dynamic edges of one child frame, sorted by capture time."""

    def __init__(self, edges: Sequence[StaticTransform]) -> None:
        """Sort the edges by capture time. `edges` must not be empty."""
        self._edges = sorted(edges, key=lambda edge: edge.timestamp_ns)
        self._timestamps_ns = [edge.timestamp_ns for edge in self._edges]

    def closest(self, timestamp_ns: int) -> StaticTransform:
        """Return the edge captured closest to `timestamp_ns`."""
        after = bisect.bisect_left(self._timestamps_ns, timestamp_ns)
        candidates = self._edges[max(after - 1, 0) : after + 1]
        return min(candidates, key=lambda edge: abs(edge.timestamp_ns - timestamp_ns))


def load_world_poses(
    session: Session, sequence_id: UUID, start_ns: int, end_ns: int
) -> WorldPoses | None:
    """Load the transforms to map poses between `start_ns` and `end_ns`.

    Returns None if the sequence's recording has no stored dynamic transforms.
    """
    sequence = session.get(McapGroupSequenceTable, sequence_id)
    if sequence is None:
        return None
    dynamic_transforms = load_dynamic_transforms_around(
        session=session, recording_id=sequence.recording_id, start_ns=start_ns, end_ns=end_ns
    )
    if dynamic_transforms is None:
        return None
    return WorldPoses(
        static_transforms=load_static_transforms(
            session=session, recording_id=sequence.recording_id
        ),
        dynamic_transforms=dynamic_transforms,
    )


def _edges_with_rotation(edges: Sequence[StaticTransform]) -> list[StaticTransform]:
    return [edge for edge in edges if any(component != 0.0 for component in edge.rotation)]


def _dynamic_transforms_by_child(edges: Sequence[StaticTransform]) -> dict[str, _EdgesOfChild]:
    edges_by_child: dict[str, list[StaticTransform]] = defaultdict(list)
    for edge in edges:
        edges_by_child[edge.child_frame_id].append(edge)
    return {
        child: _EdgesOfChild(edges=child_edges) for child, child_edges in edges_by_child.items()
    }
