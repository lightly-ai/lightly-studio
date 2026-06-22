"""Tests for annotation_label_resolver - get_all functionality."""

from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.annotation.annotation_base import (
    ImageAnnotationView,
    VideoFrameAnnotationView,
)
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import annotation_resolver
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_embedding_model,
    create_image,
    create_sample_embedding,
)
from tests.resolvers.video.helpers import VideoStub, create_video_with_frames


def test_get_all_with_payload__with_pagination(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    image_1 = create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/path/to/sample2.png",
    )
    image_2 = create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/path/to/sample1.png",
    )

    car_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="car",
    )

    airplane_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="airplane",
    )

    # Create annotations
    annotation = create_annotation(
        session=db_session,
        sample_id=image_1.sample_id,
        annotation_label_id=car_label.annotation_label_id,
        collection_id=collection_id,
    )
    create_annotation(
        session=db_session,
        sample_id=image_2.sample_id,
        annotation_label_id=airplane_label.annotation_label_id,
        collection_id=collection_id,
    )

    annotations_page = annotation_resolver.get_all_with_payload(
        session=db_session,
        pagination=Paginated(limit=1, offset=0),
        collection_id=annotation.sample.collection_id,
    )

    assert annotations_page.total_count == 2
    assert len(annotations_page.annotations) == 1
    assert (
        annotations_page.annotations[0].annotation.annotation_label.annotation_label_name
        == airplane_label.annotation_label_name
    )
    assert annotations_page.annotations[0].parent_sample_data.sample_id == image_2.sample_id


def test_get_all_with_payload__with_image(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    image_1 = create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/path/to/sample2.png",
    )
    image_2 = create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/path/to/sample1.png",
    )

    car_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="car",
    )

    airplane_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="airplane",
    )

    # Create annotations
    annotation = create_annotation(
        session=db_session,
        sample_id=image_1.sample_id,
        annotation_label_id=car_label.annotation_label_id,
        collection_id=collection_id,
    )
    create_annotation(
        session=db_session,
        sample_id=image_2.sample_id,
        annotation_label_id=airplane_label.annotation_label_id,
        collection_id=collection_id,
    )

    annotations_page = annotation_resolver.get_all_with_payload(
        session=db_session,
        collection_id=annotation.sample.collection_id,
    )

    assert annotations_page.total_count == 2
    assert len(annotations_page.annotations) == 2

    assert isinstance(annotations_page.annotations[0].parent_sample_data, ImageAnnotationView)
    assert annotations_page.annotations[0].parent_sample_type == SampleType.IMAGE
    assert (
        annotations_page.annotations[0].annotation.annotation_label.annotation_label_name
        == airplane_label.annotation_label_name
    )
    assert annotations_page.annotations[0].parent_sample_data.sample_id == image_2.sample_id
    assert annotations_page.annotations[0].parent_sample_data.sample.collection_id == collection_id

    assert isinstance(annotations_page.annotations[1].parent_sample_data, ImageAnnotationView)
    assert annotations_page.annotations[0].parent_sample_type == SampleType.IMAGE
    assert (
        annotations_page.annotations[1].annotation.annotation_label.annotation_label_name
        == car_label.annotation_label_name
    )
    assert annotations_page.annotations[1].parent_sample_data.sample_id == image_1.sample_id
    assert annotations_page.annotations[1].parent_sample_data.sample.collection_id == collection_id


def test_get_all_with_payload__with_video_frame(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)

    # Create videos
    video_frame_data = create_video_with_frames(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="/path/to/sample1.mp4"),
    )

    car_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="car",
    )

    airplane_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="airplane",
    )

    # Create annotations
    annotation = create_annotation(
        session=db_session,
        sample_id=video_frame_data.frame_sample_ids[0],
        annotation_label_id=car_label.annotation_label_id,
        collection_id=collection.collection_id,
    )
    create_annotation(
        session=db_session,
        sample_id=video_frame_data.frame_sample_ids[1],
        annotation_label_id=airplane_label.annotation_label_id,
        collection_id=collection.collection_id,
    )

    annotations_page = annotation_resolver.get_all_with_payload(
        session=db_session,
        collection_id=annotation.sample.collection_id,
    )

    assert annotations_page.total_count == 2
    assert len(annotations_page.annotations) == 2

    assert isinstance(annotations_page.annotations[0].parent_sample_data, VideoFrameAnnotationView)
    assert annotations_page.annotations[0].parent_sample_type == SampleType.VIDEO
    assert (
        annotations_page.annotations[0].parent_sample_data.video.file_path_abs
        == "/path/to/sample1.mp4"
    )
    assert (
        annotations_page.annotations[0].parent_sample_data.sample_id
        == video_frame_data.frame_sample_ids[0]
    )

    assert isinstance(annotations_page.annotations[1].parent_sample_data, VideoFrameAnnotationView)
    assert annotations_page.annotations[0].parent_sample_type == SampleType.VIDEO
    assert (
        annotations_page.annotations[1].parent_sample_data.video.file_path_abs
        == "/path/to/sample1.mp4"
    )
    assert (
        annotations_page.annotations[1].parent_sample_data.sample_id
        == video_frame_data.frame_sample_ids[1]
    )


def test_get_all_with_payload__orders_by_text_embedding_similarity(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    image_1 = create_image(session=db_session, collection_id=collection_id, file_path_abs="/a.png")
    image_2 = create_image(session=db_session, collection_id=collection_id, file_path_abs="/b.png")
    label = create_annotation_label(session=db_session, root_collection_id=collection_id)

    near_annotation = create_annotation(
        session=db_session,
        sample_id=image_1.sample_id,
        annotation_label_id=label.annotation_label_id,
        collection_id=collection_id,
    )
    far_annotation = create_annotation(
        session=db_session,
        sample_id=image_2.sample_id,
        annotation_label_id=label.annotation_label_id,
        collection_id=collection_id,
    )
    annotation_collection_id = near_annotation.sample.collection_id

    embedding_model = create_embedding_model(
        session=db_session,
        collection_id=annotation_collection_id,
        embedding_dimension=2,
    )
    create_sample_embedding(
        session=db_session,
        sample_id=near_annotation.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[1.0, 0.0],
    )
    create_sample_embedding(
        session=db_session,
        sample_id=far_annotation.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[-1.0, 0.0],
    )

    annotations_page = annotation_resolver.get_all_with_payload(
        session=db_session,
        collection_id=annotation_collection_id,
        text_embedding=[1.0, 0.0],
    )

    assert annotations_page.total_count == 2
    assert annotations_page.annotations[0].annotation.sample_id == near_annotation.sample_id
    assert annotations_page.annotations[1].annotation.sample_id == far_annotation.sample_id
    near_score = annotations_page.annotations[0].similarity_score
    far_score = annotations_page.annotations[1].similarity_score
    assert near_score is not None
    assert far_score is not None
    assert near_score == pytest.approx(1.0, abs=0.01)
    assert near_score >= far_score


def test_get_all_with_payload__without_embedding_has_no_similarity_score(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    image = create_image(session=db_session, collection_id=collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=collection_id)
    annotation = create_annotation(
        session=db_session,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        collection_id=collection_id,
    )

    annotations_page = annotation_resolver.get_all_with_payload(
        session=db_session,
        collection_id=annotation.sample.collection_id,
    )

    assert annotations_page.annotations[0].similarity_score is None


def test_get_all_with_payload__filters_by_sample_ids(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    image_1 = create_image(session=db_session, collection_id=collection_id, file_path_abs="/a.png")
    image_2 = create_image(session=db_session, collection_id=collection_id, file_path_abs="/b.png")
    label = create_annotation_label(session=db_session, root_collection_id=collection_id)
    kept_annotation = create_annotation(
        session=db_session,
        sample_id=image_1.sample_id,
        annotation_label_id=label.annotation_label_id,
        collection_id=collection_id,
    )
    create_annotation(
        session=db_session,
        sample_id=image_2.sample_id,
        annotation_label_id=label.annotation_label_id,
        collection_id=collection_id,
    )
    annotation_collection_id = kept_annotation.sample.collection_id

    annotations_page = annotation_resolver.get_all_with_payload(
        session=db_session,
        collection_id=annotation_collection_id,
        filters=AnnotationsFilter(
            collection_ids=[annotation_collection_id],
            sample_ids=[kept_annotation.sample_id],
        ),
    )

    assert annotations_page.total_count == 1
    assert annotations_page.annotations[0].annotation.sample_id == kept_annotation.sample_id


def test_get_all_with_payload__with_unsupported_collection(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)

    with pytest.raises(
        ValueError,
        match=f"Collection with id {collection.collection_id} does not have a parent collection.",
    ):
        annotation_resolver.get_all_with_payload(
            session=db_session,
            pagination=Paginated(limit=1, offset=0),
            collection_id=collection.collection_id,
        )
