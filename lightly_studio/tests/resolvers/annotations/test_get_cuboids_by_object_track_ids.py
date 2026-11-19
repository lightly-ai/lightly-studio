from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.annotation.object_track import ObjectTrackCreate
from lightly_studio.resolvers import annotation_resolver, object_track_resolver
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation_label,
    create_annotations,
    create_collection,
    create_groups,
    cuboid_create,
)


def test_get_cuboids_by_object_track_ids(db_session: Session) -> None:
    group_collection_id, group_ids = create_groups(session=db_session, count=1)
    label = create_annotation_label(session=db_session, root_collection_id=group_collection_id)
    dataset_id = create_collection(session=db_session).dataset_id
    track_a, track_b, track_c = object_track_resolver.create_many(
        session=db_session,
        tracks=[
            ObjectTrackCreate(object_track_number=number, dataset_id=dataset_id)
            for number in (1, 2, 3)
        ],
    )
    cuboid_ids = annotation_resolver.create_many(
        session=db_session,
        parent_collection_id=group_collection_id,
        annotations=[
            cuboid_create(
                parent_sample_id=group_ids[0],
                annotation_label_id=label.annotation_label_id,
                object_track_id=track_id,
                px=px,
            )
            for track_id, px in ((track_a, 1.0), (track_b, 2.0), (track_c, 3.0))
        ],
    )
    create_annotations(
        session=db_session,
        collection_id=group_collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=group_ids[0],
                annotation_label_id=label.annotation_label_id,
                object_track_id=track_a,
            )
        ],
    )

    result = annotation_resolver.get_cuboids_by_object_track_ids(
        session=db_session, object_track_ids=[track_a, track_b]
    )

    assert {annotation.sample_id for annotation in result} == {cuboid_ids[0], cuboid_ids[1]}
    assert all(annotation.annotation_type == AnnotationType.CUBOID_3D for annotation in result)
    px_by_track = {
        annotation.object_track_id: annotation.cuboid_3d_details.px
        for annotation in result
        if annotation.cuboid_3d_details is not None
    }
    assert px_by_track == {track_a: 1.0, track_b: 2.0}


def test_get_cuboids_by_object_track_ids__empty(db_session: Session) -> None:
    result = annotation_resolver.get_cuboids_by_object_track_ids(
        session=db_session, object_track_ids=[]
    )

    assert result == []
