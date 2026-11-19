"""Tests for has_cuboid_on_parent_sample resolver."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.annotation.object_track import ObjectTrackCreate
from lightly_studio.resolvers import annotation_resolver, collection_resolver, object_track_resolver
from tests.helpers_resolvers import create_annotation_label, create_groups, cuboid_create


def test_has_cuboid_on_parent_sample(db_session: Session) -> None:
    parent_collection_id, group_ids = create_groups(session=db_session, count=2)
    group_collection = collection_resolver.get_by_id(
        session=db_session, collection_id=parent_collection_id
    )
    assert group_collection is not None
    label = create_annotation_label(
        session=db_session, root_collection_id=parent_collection_id, label_name="truck"
    )
    track_id, other_track_id = object_track_resolver.create_many(
        session=db_session,
        tracks=[
            ObjectTrackCreate(object_track_number=1, dataset_id=group_collection.dataset_id),
            ObjectTrackCreate(object_track_number=2, dataset_id=group_collection.dataset_id),
        ],
    )
    annotation_resolver.create_many(
        session=db_session,
        parent_collection_id=parent_collection_id,
        annotations=[
            cuboid_create(
                parent_sample_id=group_ids[0],
                annotation_label_id=label.annotation_label_id,
                object_track_id=track_id,
            )
        ],
    )

    assert object_track_resolver.has_cuboid_on_parent_sample(
        session=db_session, object_track_id=track_id, parent_sample_id=group_ids[0]
    )
    assert not object_track_resolver.has_cuboid_on_parent_sample(
        session=db_session, object_track_id=track_id, parent_sample_id=group_ids[1]
    )
    assert not object_track_resolver.has_cuboid_on_parent_sample(
        session=db_session, object_track_id=other_track_id, parent_sample_id=group_ids[0]
    )
