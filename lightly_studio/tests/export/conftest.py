from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import (
    AnnotationCreate,
    AnnotationType,
)
from lightly_studio.models.annotation.object_track import ObjectTrackCreate
from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.resolvers import annotation_resolver, object_track_resolver
from tests.helpers_resolvers import (
    create_annotation_label,
    create_collection,
    create_image,
)
from tests.resolvers.video.helpers import VideoStub, create_video_with_frames


@pytest.fixture
def collection_with_annotations(
    db_session: Session,
) -> CollectionTable:
    """Creates a collection with samples, labels and annotations.

    Note: Confidence denominators are powers of 2 to allow precise float comparisons in tests.
    """
    collection = create_collection(session=db_session, collection_name="test_collection")
    s1 = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="img1",
        width=100,
        height=100,
    )
    s2 = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="img2",
        width=200,
        height=200,
    )
    create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="img3",
        width=300,
        height=300,
    )
    dog_label = create_annotation_label(
        session=db_session, dataset_id=collection.collection_id, label_name="dog"
    )
    cat_label = create_annotation_label(
        session=db_session, dataset_id=collection.collection_id, label_name="cat"
    )
    create_annotation_label(
        session=db_session, dataset_id=collection.collection_id, label_name="zebra"
    )

    # Create annotations:
    # - s1: dog, cat
    # - s2: dog
    # - s3: (none)
    annotation_resolver.create_many(
        session=db_session,
        parent_collection_id=collection.collection_id,
        annotations=[
            AnnotationCreate(
                parent_sample_id=s1.sample_id,
                annotation_label_id=dog_label.annotation_label_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
                confidence=None,
                x=10,
                y=10,
                width=10,
                height=10,
            ),
            AnnotationCreate(
                parent_sample_id=s1.sample_id,
                annotation_label_id=cat_label.annotation_label_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
                confidence=2 / 8,
                x=20,
                y=20,
                width=20,
                height=20,
            ),
            AnnotationCreate(
                parent_sample_id=s2.sample_id,
                annotation_label_id=dog_label.annotation_label_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
                confidence=3 / 8,
                x=30,
                y=30,
                width=30,
                height=30,
            ),
        ],
    )
    return collection


@pytest.fixture
def video_collection_with_annotations(
    db_session: Session,
) -> CollectionTable:
    """Creates a VIDEO collection with video samples, labels and annotations."""
    collection = create_collection(
        session=db_session,
        collection_name="test_video_collection",
        sample_type=SampleType.VIDEO,
    )
    video_with_frames = create_video_with_frames(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="video_001.mp4", width=3, height=2, duration_s=2.0, fps=1.0),
    )
    cat_label = create_annotation_label(
        session=db_session, dataset_id=collection.collection_id, label_name="cat"
    )
    create_annotation_label(
        session=db_session, dataset_id=collection.collection_id, label_name="dog"
    )
    object_track_ids = object_track_resolver.create_many(
        session=db_session,
        tracks=[ObjectTrackCreate(object_track_number=99, dataset_id=collection.collection_id)],
    )
    frame_0, _frame_1 = video_with_frames.frame_sample_ids
    annotation_resolver.create_many(
        session=db_session,
        parent_collection_id=video_with_frames.video_frames_collection_id,
        annotations=[
            AnnotationCreate(
                parent_sample_id=frame_0,
                annotation_label_id=cat_label.annotation_label_id,
                annotation_type=AnnotationType.INSTANCE_SEGMENTATION,
                x=0,
                y=1,
                width=1,
                height=1,
                segmentation_mask=[1, 1, 4],
                object_track_id=object_track_ids[0],
            ),
        ],
    )
    return collection
