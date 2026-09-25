"""Tests for creating cuboid_3d annotations."""

from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationCreate, AnnotationType
from lightly_studio.models.annotation.object_track import ObjectTrackCreate
from lightly_studio.resolvers import (
    annotation_resolver,
    collection_resolver,
    object_track_resolver,
)
from tests.helpers_resolvers import (
    create_annotation_label,
    create_groups,
    cuboid_create,
)


def test_create_many__cuboid_3d(db_session: Session) -> None:
    parent_collection_id, group_ids = create_groups(session=db_session)
    group_id = group_ids[0]
    label = create_annotation_label(
        session=db_session, root_collection_id=parent_collection_id, label_name="truck"
    )

    annotation_ids = annotation_resolver.create_many(
        session=db_session,
        parent_collection_id=parent_collection_id,
        annotations=[
            cuboid_create(
                parent_sample_id=group_id,
                annotation_label_id=label.annotation_label_id,
            )
        ],
        collection_name="ground_truth",
    )

    annotation = annotation_resolver.get_by_id(session=db_session, annotation_id=annotation_ids[0])
    assert annotation is not None
    assert annotation.parent_sample_id == group_id
    assert annotation.annotation_type == AnnotationType.CUBOID_3D
    assert annotation.cuboid_3d_details is not None
    assert annotation.cuboid_3d_details.frame_id == "odom"
    assert annotation.cuboid_3d_details.px == pytest.approx(1.0)
    assert annotation.cuboid_3d_details.sx == pytest.approx(2.0)
    assert annotation.cuboid_3d_details.interpolated is False

    view = annotation_resolver.get_all_by_parent_sample_ids(
        session=db_session, parent_sample_ids=[group_id]
    )
    assert len(view) == 1
    assert view[0].cuboid_3d_details is not None


def test_create_many__cuboid_3d_with_object_track(db_session: Session) -> None:
    parent_collection_id, group_ids = create_groups(session=db_session, count=2)
    group_collection = collection_resolver.get_by_id(
        session=db_session, collection_id=parent_collection_id
    )
    assert group_collection is not None
    label = create_annotation_label(
        session=db_session, root_collection_id=parent_collection_id, label_name="truck"
    )
    track_ids = object_track_resolver.create_many(
        session=db_session,
        tracks=[ObjectTrackCreate(object_track_number=1, dataset_id=group_collection.dataset_id)],
    )

    annotation_resolver.create_many(
        session=db_session,
        parent_collection_id=parent_collection_id,
        annotations=[
            cuboid_create(
                parent_sample_id=group_ids[0],
                annotation_label_id=label.annotation_label_id,
                object_track_id=track_ids[0],
            ),
            cuboid_create(
                parent_sample_id=group_ids[1],
                annotation_label_id=label.annotation_label_id,
                object_track_id=track_ids[0],
            ),
        ],
        collection_name="ground_truth",
    )

    tracked = annotation_resolver.get_all_by_object_track_id(
        session=db_session, object_track_id=track_ids[0]
    )
    assert len(tracked) == 2


def test_create_many__cuboid_3d__missing_pose(db_session: Session) -> None:
    parent_collection_id, group_ids = create_groups(session=db_session)
    group_id = group_ids[0]
    label = create_annotation_label(
        session=db_session, root_collection_id=parent_collection_id, label_name="truck"
    )

    with pytest.raises(ValueError, match="cuboid_3d is required"):
        annotation_resolver.create_many(
            session=db_session,
            parent_collection_id=parent_collection_id,
            annotations=[
                AnnotationCreate(
                    annotation_label_id=label.annotation_label_id,
                    annotation_type=AnnotationType.CUBOID_3D,
                    parent_sample_id=group_id,
                )
            ],
        )
