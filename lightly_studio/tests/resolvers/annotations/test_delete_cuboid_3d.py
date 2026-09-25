"""Tests for deleting and relinking cuboid_3d annotations."""

from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.models.annotation.cuboid_3d import Cuboid3DAnnotationTable
from lightly_studio.models.annotation.object_track import ObjectTrackCreate
from lightly_studio.resolvers import (
    annotation_resolver,
    collection_resolver,
    object_track_resolver,
)
from tests.helpers_resolvers import create_annotation_label, create_groups, cuboid_create


def test_delete_annotation__cuboid_3d(db_session: Session) -> None:
    parent_collection_id, group_ids = create_groups(session=db_session)
    label = create_annotation_label(
        session=db_session, root_collection_id=parent_collection_id, label_name="truck"
    )
    annotation_ids = annotation_resolver.create_many(
        session=db_session,
        parent_collection_id=parent_collection_id,
        annotations=[
            cuboid_create(
                parent_sample_id=group_ids[0],
                annotation_label_id=label.annotation_label_id,
            )
        ],
    )
    annotation_id = annotation_ids[0]
    assert db_session.get(Cuboid3DAnnotationTable, annotation_id) is not None

    annotation_resolver.delete_annotation(session=db_session, annotation_id=annotation_id)

    assert annotation_resolver.get_by_id(session=db_session, annotation_id=annotation_id) is None
    assert db_session.get(Cuboid3DAnnotationTable, annotation_id) is None


def test_add_annotation_to_object_track__cuboid_3d(db_session: Session) -> None:
    parent_collection_id, group_ids = create_groups(session=db_session)
    group_collection = collection_resolver.get_by_id(
        session=db_session, collection_id=parent_collection_id
    )
    assert group_collection is not None
    label = create_annotation_label(
        session=db_session, root_collection_id=parent_collection_id, label_name="truck"
    )
    annotation_ids = annotation_resolver.create_many(
        session=db_session,
        parent_collection_id=parent_collection_id,
        annotations=[
            cuboid_create(
                parent_sample_id=group_ids[0],
                annotation_label_id=label.annotation_label_id,
            )
        ],
    )
    track_ids = object_track_resolver.create_many(
        session=db_session,
        tracks=[ObjectTrackCreate(object_track_number=1, dataset_id=group_collection.dataset_id)],
    )

    result = object_track_resolver.add_annotation_to_object_track(
        session=db_session,
        annotation_id=annotation_ids[0],
        object_track_id=track_ids[0],
    )
    assert result.object_track_id == track_ids[0]
    assert result.cuboid_3d_details is not None
    assert result.cuboid_3d_details.frame_id == "odom"

    fetched = annotation_resolver.get_by_id(session=db_session, annotation_id=annotation_ids[0])
    assert fetched is not None
    assert fetched.object_track_id == track_ids[0]
    assert fetched.cuboid_3d_details is not None
    assert fetched.cuboid_3d_details.sx == 2.0


def test_add_annotation_to_object_track__duplicate_cuboid_on_group(
    db_session: Session,
) -> None:
    parent_collection_id, group_ids = create_groups(session=db_session)
    group_collection = collection_resolver.get_by_id(
        session=db_session,
        collection_id=parent_collection_id,
    )
    assert group_collection is not None
    label = create_annotation_label(
        session=db_session,
        root_collection_id=parent_collection_id,
        label_name="truck",
    )
    annotation_ids = annotation_resolver.create_many(
        session=db_session,
        parent_collection_id=parent_collection_id,
        annotations=[
            cuboid_create(
                parent_sample_id=group_ids[0],
                annotation_label_id=label.annotation_label_id,
            ),
            cuboid_create(
                parent_sample_id=group_ids[0],
                annotation_label_id=label.annotation_label_id,
            ),
        ],
    )
    (track_id,) = object_track_resolver.create_many(
        session=db_session,
        tracks=[
            ObjectTrackCreate(
                object_track_number=1,
                dataset_id=group_collection.dataset_id,
            )
        ],
    )
    object_track_resolver.add_annotation_to_object_track(
        session=db_session,
        annotation_id=annotation_ids[0],
        object_track_id=track_id,
    )

    with pytest.raises(ValueError, match="already exists on this group"):
        object_track_resolver.add_annotation_to_object_track(
            session=db_session,
            annotation_id=annotation_ids[1],
            object_track_id=track_id,
        )
