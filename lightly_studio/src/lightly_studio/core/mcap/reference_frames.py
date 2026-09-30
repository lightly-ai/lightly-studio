"""Coordinate frames a recording's scene can be shown in."""

from __future__ import annotations

from collections.abc import Sequence

from lightly_studio.core.mcap.errors import McapAccessError
from lightly_studio.core.mcap.type_definitions import StaticTransform


def check_reference_frame_ids(frame_ids: Sequence[str] | None) -> None:
    """Reject a blank or repeated frame id.

    `None` means the frames are chosen from the transform tree.

    Args:
        frame_ids: The coordinate frame ids to show, in menu order, or `None`.

    Raises:
        ValueError: If a frame id is empty or listed more than once.
    """
    if frame_ids is None:
        return
    seen: set[str] = set()
    for frame_id in frame_ids:
        if frame_id == "":
            raise ValueError("A reference frame id is empty.")
        if frame_id in seen:
            raise ValueError(f"Reference frame '{frame_id}' is listed more than once.")
        seen.add(frame_id)


def known_reference_frame_ids(
    frame_ids: Sequence[str],
    static_transforms: Sequence[StaticTransform],
    dynamic_edges: Sequence[tuple[str, str]],
) -> list[str]:
    """Return `frame_ids` when each one is a frame in the recording.

    The order is kept. The first frame is the default in the viewer. An empty list
    stores no frames, so the viewer shows none.

    Args:
        frame_ids: The coordinate frame ids to show, in menu order.
        static_transforms: The static edges stored for the recording.
        dynamic_edges: The parent and child frame of each dynamic edge.

    Returns:
        `frame_ids` as a list.

    Raises:
        McapAccessError: If a frame is not a parent or a child of a transform.
    """
    known = _known_frame_ids(static_transforms=static_transforms, dynamic_edges=dynamic_edges)
    missing = [frame_id for frame_id in frame_ids if frame_id not in known]
    if missing:
        listed = ", ".join(missing)
        raise McapAccessError(f"Reference frames are not in the recording: {listed}.")
    return list(frame_ids)


def reference_frame_ids(
    static_transforms: Sequence[StaticTransform],
    dynamic_edges: Sequence[tuple[str, str]],
) -> list[str]:
    """Return the frames a scene can be shown in.

    The list is the root frames, their direct children, and the children of those
    children. A root is a parent that is never a child. A lidar mounted on `CABIN`
    is included. A frame mounted on that lidar stays out. Dynamic roots, such as
    `map`, come first and are the default. Each group is sorted by frame id.

    Args:
        static_transforms: The static edges stored for the recording.
        dynamic_edges: The parent and child frame of each dynamic edge, one pair per
            edge. The pose is not used.

    Returns:
        The reference frame ids, in display order.
    """
    edges = [
        *((transform.parent_frame_id, transform.child_frame_id) for transform in static_transforms),
        *dynamic_edges,
    ]
    parents = {parent for parent, _child in edges}
    children = {child for _parent, child in edges}
    roots = parents - children
    dynamic_parents = {parent for parent, _child in dynamic_edges}
    ordered_roots = [*sorted(roots & dynamic_parents), *sorted(roots - dynamic_parents)]
    direct_children = _children_of(edges=edges, parents=set(ordered_roots))
    grandchildren = _children_of(
        edges=edges, parents=set(direct_children), excluded={*ordered_roots, *direct_children}
    )
    return [*ordered_roots, *direct_children, *grandchildren]


def _known_frame_ids(
    static_transforms: Sequence[StaticTransform],
    dynamic_edges: Sequence[tuple[str, str]],
) -> set[str]:
    """Return every frame that is a parent or a child of a transform."""
    frames: set[str] = set()
    for transform in static_transforms:
        frames.add(transform.parent_frame_id)
        frames.add(transform.child_frame_id)
    for parent, child in dynamic_edges:
        frames.add(parent)
        frames.add(child)
    return frames


def _children_of(
    edges: Sequence[tuple[str, str]], parents: set[str], excluded: set[str] | None = None
) -> list[str]:
    """Return the direct children of `parents`, sorted by frame id."""
    skip = parents if excluded is None else excluded
    return sorted({child for parent, child in edges if parent in parents and child not in skip})
