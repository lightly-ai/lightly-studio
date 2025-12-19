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
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)
from tests.resolvers.video.helpers import VideoStub, create_video_with_frames


def test_get_all_with_payload__with_pagination(
    test_db: Session,
) -> None:
    dataset = create_collection(session=test_db)
    dataset_id = dataset.collection_id

    image_1 = create_image(
        session=test_db,
        collection_id=dataset_id,
        file_path_abs="/path/to/sample2.png",
    )
    image_2 = create_image(
        session=test_db,
        collection_id=dataset_id,
        file_path_abs="/path/to/sample1.png",
    )

    car_label = create_annotation_label(
        session=test_db,
        root_dataset_id=dataset_id,
        label_name="car",
    )

    airplane_label = create_annotation_label(
        session=test_db,
        root_dataset_id=dataset_id,
        label_name="airplane",
    )

    # Create annotations
    annotation = create_annotation(
        session=test_db,
        sample_id=image_1.sample_id,
        annotation_label_id=car_label.annotation_label_id,
        collection_id=dataset_id,
    )
    create_annotation(
        session=test_db,
        sample_id=image_2.sample_id,
        annotation_label_id=airplane_label.annotation_label_id,
        collection_id=dataset_id,
    )

    annotations_page = annotation_resolver.get_all_with_payload(
        session=test_db,
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
    test_db: Session,
) -> None:
    dataset = create_collection(session=test_db)
    dataset_id = dataset.collection_id

    image_1 = create_image(
        session=test_db,
        collection_id=dataset_id,
        file_path_abs="/path/to/sample2.png",
    )
    image_2 = create_image(
        session=test_db,
        collection_id=dataset_id,
        file_path_abs="/path/to/sample1.png",
    )

    car_label = create_annotation_label(
        session=test_db,
        root_dataset_id=dataset_id,
        label_name="car",
    )

    airplane_label = create_annotation_label(
        session=test_db,
        root_dataset_id=dataset_id,
        label_name="airplane",
    )

    # Create annotations
    annotation = create_annotation(
        session=test_db,
        sample_id=image_1.sample_id,
        annotation_label_id=car_label.annotation_label_id,
        collection_id=dataset_id,
    )
    create_annotation(
        session=test_db,
        sample_id=image_2.sample_id,
        annotation_label_id=airplane_label.annotation_label_id,
        collection_id=dataset_id,
    )

    annotations_page = annotation_resolver.get_all_with_payload(
        session=test_db,
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
    assert annotations_page.annotations[0].parent_sample_data.sample.collection_id == dataset_id

    assert isinstance(annotations_page.annotations[1].parent_sample_data, ImageAnnotationView)
    assert annotations_page.annotations[0].parent_sample_type == SampleType.IMAGE
    assert (
        annotations_page.annotations[1].annotation.annotation_label.annotation_label_name
        == car_label.annotation_label_name
    )
    assert annotations_page.annotations[1].parent_sample_data.sample_id == image_1.sample_id
    assert annotations_page.annotations[1].parent_sample_data.sample.collection_id == dataset_id


def test_get_all_with_payload__with_video_frame(test_db: Session) -> None:
    dataset = create_collection(session=test_db, sample_type=SampleType.VIDEO)

    # Create videos
    video_frame_data = create_video_with_frames(
        session=test_db,
        collection_id=dataset.collection_id,
        video=VideoStub(path="/path/to/sample1.mp4"),
    )

    car_label = create_annotation_label(
        session=test_db,
        root_dataset_id=dataset.collection_id,
        label_name="car",
    )

    airplane_label = create_annotation_label(
        session=test_db,
        root_dataset_id=dataset.collection_id,
        label_name="airplane",
    )

    # Create annotations
    annotation = create_annotation(
        session=test_db,
        sample_id=video_frame_data.frame_sample_ids[0],
        annotation_label_id=car_label.annotation_label_id,
        collection_id=dataset.collection_id,
    )
    create_annotation(
        session=test_db,
        sample_id=video_frame_data.frame_sample_ids[1],
        annotation_label_id=airplane_label.annotation_label_id,
        collection_id=dataset.collection_id,
    )

    annotations_page = annotation_resolver.get_all_with_payload(
        session=test_db,
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


def test_get_all_with_payload__with_unsupported_dataset(
    test_db: Session,
) -> None:
    dataset = create_collection(session=test_db, sample_type=SampleType.VIDEO)

    with pytest.raises(
        ValueError,
        match=f"Collection with id {dataset.collection_id} does not have a parent collection.",
    ):
        annotation_resolver.get_all_with_payload(
            session=test_db,
            pagination=Paginated(limit=1, offset=0),
            collection_id=dataset.collection_id,
        )
