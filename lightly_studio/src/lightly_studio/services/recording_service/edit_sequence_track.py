"""Create and extend workspace-managed cuboid tracks."""

from __future__ import annotations

import math
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import func
from sqlmodel import Session, col, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation.cuboid_3d import Cuboid3DAnnotationTable
from lightly_studio.models.annotation.object_track import ObjectTrackTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.sequence import SampleSequenceLinkTable
from lightly_studio.resolvers import sequence_resolver
from lightly_studio.resolvers.annotation_resolver import annotation_helper
from lightly_studio.services.recording_service.get_ticks import get_ticks

_SLERP_LINEAR_THRESHOLD = 0.9995


class IntervalMode(str, Enum):
    """How to fill ticks between authored cuboids."""

    HOLD = "hold"
    INTERPOLATE = "interpolate"


def start_track(
    session: Session, dataset_id: UUID, sequence_id: UUID, annotation_id: UUID
) -> ObjectTrackTable:
    """Attach an existing untracked cuboid as the first authored track keyframe."""
    _validate_sequence(session=session, dataset_id=dataset_id, sequence_id=sequence_id)
    annotation, _ = _get_cuboid(session=session, annotation_id=annotation_id)
    _get_tick_link(session=session, sequence_id=sequence_id, annotation=annotation)
    if annotation.object_track_id is not None:
        raise ValueError("The annotation already belongs to a track.")

    next_number = session.exec(
        select(func.max(ObjectTrackTable.object_track_number)).where(
            col(ObjectTrackTable.dataset_id) == dataset_id
        )
    ).one()
    track = ObjectTrackTable(
        object_track_number=(next_number or 0) + 1,
        dataset_id=dataset_id,
        managed=True,
        sequence_sample_id=sequence_id,
    )
    try:
        session.add(track)
        session.flush()
        annotation_helper.update_annotation_object(
            session=session,
            annotation=annotation,
            fields_to_update={"object_track_id": track.object_track_id},
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    return track


# Six identifiers and inputs are intrinsic to this sequence-scoped operation.
def extend_track(  # noqa: PLR0913
    session: Session,
    dataset_id: UUID,
    sequence_id: UUID,
    track_id: UUID,
    annotation_id: UUID,
    mode: IntervalMode,
) -> ObjectTrackTable:
    """Use a later cuboid as a keyframe and fill the intervening sequence ticks atomically."""
    _validate_sequence(session=session, dataset_id=dataset_id, sequence_id=sequence_id)
    track = session.get(ObjectTrackTable, track_id)
    if track is None or track.dataset_id != dataset_id or track.sequence_sample_id != sequence_id:
        raise ValueError("Track does not belong to this sequence.")
    if not track.managed:
        raise ValueError("Existing imported tracks are read-only.")
    target, target_cuboid = _get_cuboid(session=session, annotation_id=annotation_id)
    target_link = _get_tick_link(session=session, sequence_id=sequence_id, annotation=target)
    if target.object_track_id == track_id:
        return track  # A repeated request has already committed this keyframe.
    if target.object_track_id is not None:
        raise ValueError("The annotation already belongs to a track.")

    anchor, anchor_cuboid, anchor_link = _last_keyframe(
        session=session, sequence_id=sequence_id, track_id=track_id
    )
    if target_link.seq_number <= anchor_link.seq_number:
        raise ValueError("The next keyframe must be on a later tick.")
    if target.annotation_label_id != anchor.annotation_label_id:
        raise ValueError("Track keyframes must use the same annotation class.")
    if target.annotation_collection_id != anchor.annotation_collection_id:
        raise ValueError("Track keyframes must use the same annotation source.")
    if target_cuboid.frame_id != anchor_cuboid.frame_id:
        raise ValueError("Track keyframes must use the same coordinate frame.")

    links = sequence_resolver.get_sample_links(session=session, sequence_sample_id=sequence_id)
    anchor_index = links.index(anchor_link)
    target_index = links.index(target_link)
    between = links[anchor_index + 1 : target_index]
    generated = [
        _interpolate_cuboid(
            anchor=anchor_cuboid,
            target=target_cuboid,
            fraction=_fraction(anchor_link, target_link, link, anchor_index, target_index, index),
            mode=mode,
        )
        for index, link in enumerate(between, start=anchor_index + 1)
    ]
    try:
        annotation_helper.update_annotation_object(
            session=session,
            annotation=target,
            fields_to_update={"object_track_id": track_id},
        )
        _insert_generated(
            session=session,
            track_id=track_id,
            anchor=anchor,
            links=between,
            cuboids=generated,
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    return track


def _validate_sequence(session: Session, dataset_id: UUID, sequence_id: UUID) -> None:
    if get_ticks(session=session, dataset_id=dataset_id, sequence_id=sequence_id) is None:
        raise ValueError("MCAP sequence not found in this dataset.")


def _get_cuboid(
    session: Session, annotation_id: UUID
) -> tuple[AnnotationBaseTable, Cuboid3DAnnotationTable]:
    annotation = session.get(AnnotationBaseTable, annotation_id)
    cuboid = session.get(Cuboid3DAnnotationTable, annotation_id)
    if annotation is None or cuboid is None:
        raise ValueError("Cuboid annotation not found.")
    return annotation, cuboid


def _get_tick_link(
    session: Session, sequence_id: UUID, annotation: AnnotationBaseTable
) -> SampleSequenceLinkTable:
    link = session.get(SampleSequenceLinkTable, annotation.parent_sample_id)
    if link is None or link.sequence_sample_id != sequence_id:
        raise ValueError("Annotation is not attached to this sequence.")
    return link


def _last_keyframe(
    session: Session, sequence_id: UUID, track_id: UUID
) -> tuple[AnnotationBaseTable, Cuboid3DAnnotationTable, SampleSequenceLinkTable]:
    statement = (
        select(AnnotationBaseTable, Cuboid3DAnnotationTable, SampleSequenceLinkTable)
        .join(
            Cuboid3DAnnotationTable,
            col(Cuboid3DAnnotationTable.sample_id) == col(AnnotationBaseTable.sample_id),
        )
        .join(
            SampleSequenceLinkTable,
            col(SampleSequenceLinkTable.sample_id) == col(AnnotationBaseTable.parent_sample_id),
        )
        .where(
            col(AnnotationBaseTable.object_track_id) == track_id,
            col(SampleSequenceLinkTable.sequence_sample_id) == sequence_id,
            col(Cuboid3DAnnotationTable.interpolated).is_(False),
        )
        .order_by(col(SampleSequenceLinkTable.seq_number).desc())
    )
    result = session.exec(statement).first()
    if result is None:
        raise ValueError("Track has no authored keyframe in this sequence.")
    return result


def _fraction(  # noqa: PLR0913
    anchor_link: SampleSequenceLinkTable,
    target_link: SampleSequenceLinkTable,
    link: SampleSequenceLinkTable,
    anchor_index: int,
    target_index: int,
    index: int,
) -> float:
    start, end, current = (
        anchor_link.timestamp_ns,
        target_link.timestamp_ns,
        link.timestamp_ns,
    )
    if start is not None and end is not None and current is not None and start < current < end:
        return (current - start) / (end - start)
    return (index - anchor_index) / (target_index - anchor_index)


def _interpolate_cuboid(
    anchor: Cuboid3DAnnotationTable,
    target: Cuboid3DAnnotationTable,
    fraction: float,
    mode: IntervalMode,
) -> Cuboid3DAnnotationTable:
    if mode is IntervalMode.HOLD:
        fraction = 0.0
    rotation = _slerp(
        (anchor.qx, anchor.qy, anchor.qz, anchor.qw),
        (target.qx, target.qy, target.qz, target.qw),
        fraction,
    )

    def mix(a: float, b: float) -> float:
        return a + (b - a) * fraction

    return Cuboid3DAnnotationTable(
        frame_id=anchor.frame_id,
        px=mix(anchor.px, target.px),
        py=mix(anchor.py, target.py),
        pz=mix(anchor.pz, target.pz),
        qx=rotation[0],
        qy=rotation[1],
        qz=rotation[2],
        qw=rotation[3],
        sx=mix(anchor.sx, target.sx),
        sy=mix(anchor.sy, target.sy),
        sz=mix(anchor.sz, target.sz),
        interpolated=True,
    )


def _slerp(start: tuple[float, ...], end: tuple[float, ...], fraction: float) -> tuple[float, ...]:
    dot = sum(a * b for a, b in zip(start, end))
    if dot < 0:
        end = tuple(-value for value in end)
        dot = -dot
    if dot > _SLERP_LINEAR_THRESHOLD:
        result = tuple(a + (b - a) * fraction for a, b in zip(start, end))
    else:
        angle = math.acos(min(1.0, dot))
        scale = math.sin(angle)
        result = tuple(
            (math.sin((1 - fraction) * angle) * a + math.sin(fraction * angle) * b) / scale
            for a, b in zip(start, end)
        )
    norm = math.sqrt(sum(value * value for value in result))
    return tuple(value / norm for value in result)


def _insert_generated(
    session: Session,
    track_id: UUID,
    anchor: AnnotationBaseTable,
    links: list[SampleSequenceLinkTable],
    cuboids: list[Cuboid3DAnnotationTable],
) -> None:
    for link, cuboid in zip(links, cuboids):
        annotation_id = uuid4()
        session.add(
            SampleTable(sample_id=annotation_id, collection_id=anchor.annotation_collection_id)
        )
        session.flush()
        session.add(
            AnnotationBaseTable(
                sample_id=annotation_id,
                parent_sample_id=link.sample_id,
                annotation_type=anchor.annotation_type,
                annotation_label_id=anchor.annotation_label_id,
                object_track_id=track_id,
            )
        )
        session.flush()
        cuboid.sample_id = annotation_id
        session.add(cuboid)
