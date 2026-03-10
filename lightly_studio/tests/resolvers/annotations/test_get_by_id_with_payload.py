"""Tests for annotation_label_resolver - get_all functionality."""

from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import (
    ImageAnnotationDetailsView,
    VideoFrameAnnotationDetailsView,
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


def test_get_by_id__with_image(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    image_1 = create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/path/to/sample2.png",
    )

    car_label = create_annotation_label(
        session=db_session,
        dataset_id=collection_id,
        label_name="car",
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
        sample_id=image_1.sample_id,
        annotation_label_id=car_label.annotation_label_id,
        collection_id=collection_id,
    )

    annotation_with_payload = annotation_resolver.get_by_id_with_payload(
        session=db_session,
        sample_id=annotation.sample_id,
    )

    assert annotation_with_payload is not None
    assert (
        annotation_with_payload.annotation.annotation_label.annotation_label_name
        == car_label.annotation_label_name
    )
    assert isinstance(annotation_with_payload.parent_sample_data, ImageAnnotationDetailsView)
    assert annotation_with_payload.parent_sample_data.file_path_abs == image_1.file_path_abs
    assert annotation_with_payload.parent_sample_data.sample.sample_id == image_1.sample.sample_id


def test_get_all_with_payload__with_video_frame(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)

    video_frame_data = create_video_with_frames(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="/path/to/sample1.mp4"),
    )

    car_label = create_annotation_label(
        session=db_session,
        dataset_id=collection.collection_id,
        label_name="car",
    )

    # Create annotations
    annotation = create_annotation(
        session=db_session,
        sample_id=video_frame_data.frame_sample_ids[0],
        annotation_label_id=car_label.annotation_label_id,
        collection_id=video_frame_data.video_frames_collection_id,
    )

    annotation_with_payload = annotation_resolver.get_by_id_with_payload(
        session=db_session,
        sample_id=annotation.sample_id,
    )
    assert annotation_with_payload is not None
    assert (
        annotation_with_payload.annotation.annotation_label.annotation_label_name
        == car_label.annotation_label_name
    )
    assert isinstance(annotation_with_payload.parent_sample_data, VideoFrameAnnotationDetailsView)
    assert annotation_with_payload.parent_sample_data.video.file_path_abs == "/path/to/sample1.mp4"
    assert annotation_with_payload.parent_sample_type == SampleType.VIDEO_FRAME


def test_get_all_with_payload__with_no_parent_collection(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)

    sample_id = create_video_with_frames(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="/path/to/sample1.mp4"),
    ).video_sample_id

    with pytest.raises(
        ValueError,
        match=f"Sample with id {sample_id} does not have a parent collection.",
    ):
        annotation_resolver.get_by_id_with_payload(session=db_session, sample_id=sample_id)
