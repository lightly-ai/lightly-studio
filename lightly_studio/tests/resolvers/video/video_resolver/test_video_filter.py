"""Tests for VideoFilter."""

from __future__ import annotations

from uuid import UUID

import pytest
from sqlmodel import Session, col, select

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.collection import SampleType
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.video import VideoTable
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation_label,
    create_annotations,
    create_collection,
)
from tests.resolvers.video.helpers import VideoStub, create_video, create_video_with_frames


def test_query__annotation_filter(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    video_with_annotation = create_video_with_frames(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="with_annotation.mp4"),
    )
    create_video_with_frames(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="without_annotation.mp4"),
    )
    label = create_annotation_label(
        session=db_session,
        root_collection_id=video_with_annotation.video_frames_collection_id,
        label_name="car",
    )
    create_annotations(
        session=db_session,
        collection_id=video_with_annotation.video_frames_collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=video_with_annotation.frame_sample_ids[0],
                annotation_label_id=label.annotation_label_id,
            )
        ],
    )

    query = select(VideoTable).join(VideoTable.sample)
    video_filter = VideoFilter(
        frame_annotation_filter=AnnotationsFilter(
            annotation_label_ids=[label.annotation_label_id],
        )
    )

    filtered_query = video_filter.apply(query=query)
    result = db_session.exec(filtered_query).all()
    assert len(result) == 1
    assert result[0].sample_id == video_with_annotation.video_sample_id


def test_query__annotation_filter__direct_video_annotations(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    video_with_annotation = create_video(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="with_annotation.mp4"),
    )
    create_video(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="without_annotation.mp4"),
    )
    label = create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="running",
    )
    create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=video_with_annotation.sample_id,
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.CLASSIFICATION,
            )
        ],
    )

    query = select(VideoTable).join(VideoTable.sample)
    video_filter = VideoFilter(
        frame_annotation_filter=AnnotationsFilter(
            annotation_label_ids=[label.annotation_label_id],
        )
    )

    filtered_query = video_filter.apply(query=query)
    result = db_session.exec(filtered_query).all()
    assert len(result) == 1
    assert result[0].sample_id == video_with_annotation.sample_id


@pytest.mark.parametrize(
    ("label_names", "expected_names"),
    [
        ([], ["unannotated.mp4"]),
        (["car"], ["frame_car.mp4", "unannotated.mp4"]),
    ],
)
def test_query__annotation_filter__include_unannotated_samples(
    db_session: Session, label_names: list[str], expected_names: list[str]
) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    frame_car, direct_running, _ = [
        create_video_with_frames(
            session=db_session,
            collection_id=collection.collection_id,
            video=VideoStub(path=path, duration_s=1.0, fps=2.0),
        )
        for path in ["frame_car.mp4", "direct_running.mp4", "unannotated.mp4"]
    ]
    car_label = create_annotation_label(
        session=db_session,
        root_collection_id=frame_car.video_frames_collection_id,
        label_name="car",
    )
    running_label = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="running"
    )
    # Only the first of the two frames has a car.
    create_annotations(
        session=db_session,
        collection_id=frame_car.video_frames_collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=frame_car.frame_sample_ids[0],
                annotation_label_id=car_label.annotation_label_id,
            )
        ],
    )
    create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=direct_running.video_sample_id,
                annotation_label_id=running_label.annotation_label_id,
                annotation_type=AnnotationType.CLASSIFICATION,
            )
        ],
    )
    labels = {"car": car_label, "running": running_label}

    video_filter = VideoFilter(
        frame_annotation_filter=AnnotationsFilter(
            annotation_label_ids=[labels[name].annotation_label_id for name in label_names],
            include_unannotated_samples=True,
        )
    )

    assert (
        _filter_video_names(
            session=db_session, video_filter=video_filter, collection_id=collection.collection_id
        )
        == expected_names
    )


def _filter_video_names(
    session: Session, video_filter: VideoFilter, collection_id: UUID
) -> list[str]:
    query = (
        select(VideoTable)
        .join(VideoTable.sample)
        .where(col(SampleTable.collection_id) == collection_id)
    )
    return sorted(video.file_name for video in session.exec(video_filter.apply(query=query)).all())
