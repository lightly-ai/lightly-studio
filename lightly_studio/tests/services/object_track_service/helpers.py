"""Helpers to build sequences with object tracks and cuboids."""

from __future__ import annotations

import math
from dataclasses import dataclass
from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationCreate,
    AnnotationType,
)
from lightly_studio.models.annotation.cuboid_3d import Cuboid3DCreate
from lightly_studio.models.annotation.object_track import ObjectTrackCreate, ObjectTrackTable
from lightly_studio.models.collection import SampleType
from lightly_studio.models.recording import RecordingFormat
from lightly_studio.models.sample import SampleCreate
from lightly_studio.models.sequence import SampleSequenceLinkCreate
from lightly_studio.resolvers import (
    annotation_resolver,
    mcap_group_sequence_resolver,
    object_track_resolver,
    recording_resolver,
    sample_resolver,
    sequence_resolver,
)
from tests.helpers_resolvers import create_annotation_label, create_collection


@dataclass
class Scene:
    dataset_id: UUID
    sequence_collection_id: UUID
    group_collection_id: UUID
    recording_id: UUID
    label_id: UUID


def create_scene(session: Session) -> Scene:
    sequence_collection = create_collection(session=session, sample_type=SampleType.SEQUENCE)
    group_collection = create_collection(
        session=session,
        sample_type=SampleType.GROUP,
        parent_collection_id=sequence_collection.collection_id,
    )
    recording_id = recording_resolver.create(
        session=session,
        dataset_id=sequence_collection.dataset_id,
        uri="/bags/drive_001.mcap",
        format_=RecordingFormat.MCAP,
    )
    label = create_annotation_label(
        session=session, root_collection_id=sequence_collection.collection_id, label_name="car"
    )
    return Scene(
        dataset_id=sequence_collection.dataset_id,
        sequence_collection_id=sequence_collection.collection_id,
        group_collection_id=group_collection.collection_id,
        recording_id=recording_id,
        label_id=label.annotation_label_id,
    )


def add_sequence(session: Session, scene: Scene, timestamps: list[int | None]) -> list[UUID]:
    sequence_sample_id = mcap_group_sequence_resolver.create(
        session=session,
        collection_id=scene.sequence_collection_id,
        recording_id=scene.recording_id,
    )
    tick_ids = sample_resolver.create_many(
        session=session,
        samples=[SampleCreate(collection_id=scene.group_collection_id) for _ in timestamps],
    )
    sequence_resolver.add_samples(
        session=session,
        sequence_sample_id=sequence_sample_id,
        links=[
            SampleSequenceLinkCreate(sample_id=tick_id, seq_number=i, timestamp_ns=timestamp)
            for i, (tick_id, timestamp) in enumerate(zip(tick_ids, timestamps))
        ],
    )
    return tick_ids


def create_track(
    session: Session, scene: Scene, number: int, parent: ObjectTrackTable | None = None
) -> ObjectTrackTable:
    track_id = object_track_resolver.create_many(
        session=session,
        tracks=[
            ObjectTrackCreate(
                object_track_number=number,
                dataset_id=scene.dataset_id,
                parent_object_track_id=parent.object_track_id if parent else None,
            )
        ],
    )[0]
    track = object_track_resolver.get_by_id(session=session, object_track_id=track_id)
    assert track is not None
    return track


def add_cuboid(  # noqa: PLR0913
    session: Session,
    scene: Scene,
    tick_id: UUID,
    track: ObjectTrackTable,
    px: float = 0.0,
    frame_id: str = "odom",
    source: str = "gt",
    label_id: UUID | None = None,
    interpolated: bool = False,
    py: float = 0.0,
    yaw_deg: float = 0.0,
) -> UUID:
    return annotation_resolver.create_many(
        session=session,
        parent_collection_id=scene.group_collection_id,
        annotations=[
            AnnotationCreate(
                annotation_label_id=label_id or scene.label_id,
                annotation_type=AnnotationType.CUBOID_3D,
                parent_sample_id=tick_id,
                object_track_id=track.object_track_id,
                cuboid_3d=Cuboid3DCreate(
                    frame_id=frame_id,
                    px=px,
                    py=py,
                    pz=0.0,
                    qx=0.0,
                    qy=0.0,
                    qz=math.sin(math.radians(yaw_deg) / 2),
                    qw=math.cos(math.radians(yaw_deg) / 2),
                    sx=4.0,
                    sy=2.0,
                    sz=1.5,
                    interpolated=interpolated,
                ),
            )
        ],
        collection_name=source,
    )[0]


def px_of(annotation: AnnotationBaseTable) -> float:
    assert annotation.cuboid_3d_details is not None
    return annotation.cuboid_3d_details.px


def track_cuboids(session: Session, track: ObjectTrackTable) -> list[AnnotationBaseTable]:
    return annotation_resolver.get_all_by_object_track_id(
        session=session, object_track_id=track.object_track_id
    )


def cuboids_by_tick(
    session: Session, track: ObjectTrackTable
) -> dict[UUID, list[AnnotationBaseTable]]:
    by_tick: dict[UUID, list[AnnotationBaseTable]] = {}
    for annotation in track_cuboids(session=session, track=track):
        by_tick.setdefault(annotation.parent_sample_id, []).append(annotation)
    return by_tick
