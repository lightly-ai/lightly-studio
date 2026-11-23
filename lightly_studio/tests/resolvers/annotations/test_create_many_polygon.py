"""Tests for creating polygon annotations."""

from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationCreate, AnnotationType
from lightly_studio.models.annotation.object_track import ObjectTrackCreate
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import (
    annotation_resolver,
    object_track_resolver,
    video_frame_resolver,
)
from tests.helpers_resolvers import (
    create_annotation_label,
    create_collection,
    create_image,
)
from tests.resolvers.video.helpers import VideoStub, create_video_with_frames


def test_create_many__polygon(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="cat"
    )

    annotation_ids = annotation_resolver.create_many(
        session=db_session,
        parent_collection_id=collection.collection_id,
        annotations=[
            AnnotationCreate(
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.POLYGON,
                parent_sample_id=image.sample_id,
                polygons=[[(1.5, 1.5), (4.0, 1.5), (4.0, 3.2)]],
            )
        ],
    )

    annotation = annotation_resolver.get_by_id(session=db_session, annotation_id=annotation_ids[0])
    assert annotation is not None
    assert annotation.annotation_type == AnnotationType.POLYGON
    assert annotation.polygon_details is not None
    assert annotation.polygon_details.polygons == [[[1.5, 1.5], [4.0, 1.5], [4.0, 3.2]]]
    assert (
        annotation.polygon_details.x,
        annotation.polygon_details.y,
        annotation.polygon_details.width,
        annotation.polygon_details.height,
    ) == (1, 1, 3, 3)


def test_create_many__polygon_ignores_box_fields(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="cat"
    )

    annotation_ids = annotation_resolver.create_many(
        session=db_session,
        parent_collection_id=collection.collection_id,
        annotations=[
            AnnotationCreate(
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.POLYGON,
                parent_sample_id=image.sample_id,
                x=100,
                y=100,
                width=100,
                height=100,
                polygons=[[(0.0, 0.0), (2.0, 0.0), (2.0, 2.0)]],
            )
        ],
    )

    annotation = annotation_resolver.get_by_id(session=db_session, annotation_id=annotation_ids[0])
    assert annotation is not None
    assert annotation.polygon_details is not None
    assert (
        annotation.polygon_details.x,
        annotation.polygon_details.y,
        annotation.polygon_details.width,
        annotation.polygon_details.height,
    ) == (0, 0, 2, 2)


def test_create_many__polygon_missing_polygons(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="cat"
    )

    with pytest.raises(ValueError, match="Polygon annotations require polygons"):
        annotation_resolver.create_many(
            session=db_session,
            parent_collection_id=collection.collection_id,
            annotations=[
                AnnotationCreate(
                    annotation_label_id=label.annotation_label_id,
                    annotation_type=AnnotationType.POLYGON,
                    parent_sample_id=image.sample_id,
                    polygons=None,
                )
            ],
        )


def test_create_many__polygon_invalid_polygons(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="cat"
    )

    with pytest.raises(ValueError, match="at least 3 vertices"):
        annotation_resolver.create_many(
            session=db_session,
            parent_collection_id=collection.collection_id,
            annotations=[
                AnnotationCreate(
                    annotation_label_id=label.annotation_label_id,
                    annotation_type=AnnotationType.POLYGON,
                    parent_sample_id=image.sample_id,
                    polygons=[[(0.0, 0.0), (2.0, 0.0)]],
                )
            ],
        )


def test_create_many__polygon_on_video_frame_with_track(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    video_with_frames = create_video_with_frames(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="/path/to/video.mp4"),
    )
    label = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="car"
    )
    track_id = object_track_resolver.create_many(
        session=db_session,
        tracks=[ObjectTrackCreate(object_track_number=1, dataset_id=collection.dataset_id)],
    )[0]

    annotation_resolver.create_many(
        session=db_session,
        parent_collection_id=video_with_frames.video_frames_collection_id,
        annotations=[
            AnnotationCreate(
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.POLYGON,
                parent_sample_id=video_with_frames.frame_sample_ids[0],
                object_track_id=track_id,
                polygons=[[(0.0, 0.0), (2.0, 0.0), (2.0, 2.0)]],
            )
        ],
    )

    frames = video_frame_resolver.get_all_by_collection_id(
        session=db_session, collection_id=video_with_frames.video_frames_collection_id
    ).samples
    frame_annotations = frames[0].sample.annotations
    assert len(frame_annotations) == 1
    assert frame_annotations[0].polygon_details is not None
    assert frame_annotations[0].polygon_details.polygons == [[[0.0, 0.0], [2.0, 0.0], [2.0, 2.0]]]
    assert frame_annotations[0].object_track_id == track_id
