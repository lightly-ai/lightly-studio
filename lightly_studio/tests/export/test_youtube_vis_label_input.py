"""Tests for the LightlyStudio YouTube-VIS instance segmentation track input adapter."""

from __future__ import annotations

from pathlib import Path

from labelformat.model.category import Category
from labelformat.model.instance_segmentation_track import (
    SingleInstanceSegmentationTrack,
    VideoInstanceSegmentationTrack,
)
from labelformat.model.video import Video
from sqlmodel import Session

from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.core.video.video_sample import VideoSample
from lightly_studio.export.youtube_vis_label_input import (
    LightlyStudioYouTubeVISInstanceSegmentationTrackInput,
)
from lightly_studio.models.annotation.annotation_base import AnnotationCreate, AnnotationType
from lightly_studio.models.annotation.object_track import ObjectTrackCreate
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import annotation_resolver, object_track_resolver
from tests.helpers_resolvers import (
    create_annotation_label,
    create_collection,
)
from tests.resolvers.video.helpers import VideoStub, create_video_with_frames


class TestLightlyStudioYouTubeVISInstanceSegmentationTrackInput:
    def test_get_categories(
        self,
        db_session: Session,
    ) -> None:
        collection = create_collection(
            session=db_session,
            sample_type=SampleType.VIDEO,
        )
        create_video_with_frames(
            session=db_session,
            collection_id=collection.collection_id,
            video=VideoStub(path="video_001.mp4"),
        )
        create_annotation_label(
            session=db_session, dataset_id=collection.collection_id, label_name="cat"
        )
        create_annotation_label(
            session=db_session, dataset_id=collection.collection_id, label_name="dog"
        )
        samples = DatasetQuery(dataset=collection, session=db_session, sample_class=VideoSample)
        label_input = LightlyStudioYouTubeVISInstanceSegmentationTrackInput(
            session=db_session,
            samples=samples,
        )
        categories = list(label_input.get_categories())
        assert categories == [
            Category(id=1, name="cat"),
            Category(id=2, name="dog"),
        ]

    def test_get_categories__no_annotations(self, db_session: Session) -> None:
        collection = create_collection(
            session=db_session,
            collection_name="video_empty",
            sample_type=SampleType.VIDEO,
        )
        create_video_with_frames(
            session=db_session,
            collection_id=collection.collection_id,
            video=VideoStub(path="v.mp4", width=10, height=10, duration_s=1.0, fps=1.0),
        )
        samples = DatasetQuery(dataset=collection, session=db_session, sample_class=VideoSample)
        label_input = LightlyStudioYouTubeVISInstanceSegmentationTrackInput(
            session=db_session,
            samples=samples,
        )
        assert list(label_input.get_categories()) == []

    def test_get_videos(
        self,
        db_session: Session,
    ) -> None:
        collection = create_collection(
            session=db_session,
            collection_name="video_multiple",
            sample_type=SampleType.VIDEO,
        )
        create_video_with_frames(
            session=db_session,
            collection_id=collection.collection_id,
            video=VideoStub(path="video_001.mp4", width=10, height=20, duration_s=1.0, fps=2.0),
        )
        create_video_with_frames(
            session=db_session,
            collection_id=collection.collection_id,
            video=VideoStub(path="video_002.mp4", width=30, height=40, duration_s=1.0, fps=3.0),
        )
        samples = DatasetQuery(dataset=collection, session=db_session, sample_class=VideoSample)
        label_input = LightlyStudioYouTubeVISInstanceSegmentationTrackInput(
            session=db_session,
            samples=samples,
        )

        assert list(label_input.get_videos()) == [
            Video(
                id=1,
                filename=Path("video_001.mp4").name,
                width=10,
                height=20,
                number_of_frames=2,
            ),
            Video(
                id=2,
                filename=Path("video_002.mp4").name,
                width=30,
                height=40,
                number_of_frames=3,
            ),
        ]

    def test_get_videos__no_videos(self, db_session: Session) -> None:
        collection = create_collection(
            session=db_session,
            collection_name="video_empty",
            sample_type=SampleType.VIDEO,
        )
        samples = DatasetQuery(dataset=collection, session=db_session, sample_class=VideoSample)
        label_input = LightlyStudioYouTubeVISInstanceSegmentationTrackInput(
            session=db_session,
            samples=samples,
        )
        assert list(label_input.get_videos()) == []

    def test_get_labels(
        self,
        db_session: Session,
    ) -> None:
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
        object_track_ids = object_track_resolver.create_many(
            session=db_session,
            tracks=[ObjectTrackCreate(object_track_number=99, dataset_id=collection.collection_id)],
        )
        annotation_resolver.create_many(
            session=db_session,
            parent_collection_id=video_with_frames.video_frames_collection_id,
            annotations=[
                AnnotationCreate(
                    parent_sample_id=video_with_frames.frame_sample_ids[0],
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
        samples = DatasetQuery(dataset=collection, session=db_session, sample_class=VideoSample)
        label_input = LightlyStudioYouTubeVISInstanceSegmentationTrackInput(
            session=db_session,
            samples=samples,
        )
        labels = list(label_input.get_labels())

        assert len(labels) == 1
        track = labels[0]
        assert isinstance(track, VideoInstanceSegmentationTrack)
        assert track.video == Video(
            id=1,
            filename=Path("video_001.mp4").name,
            width=3,
            height=2,
            number_of_frames=2,
        )
        assert len(track.objects) == 1
        obj = track.objects[0]
        assert isinstance(obj, SingleInstanceSegmentationTrack)
        assert obj.category == Category(id=1, name="cat")
        assert obj.object_track_id == 99
        assert len(obj.segmentations) == 2
        assert obj.segmentations[0]
        assert obj.segmentations[1] is None

    def test_get_labels__no_annotations(self, db_session: Session) -> None:
        collection = create_collection(
            session=db_session,
            collection_name="video_empty",
            sample_type=SampleType.VIDEO,
        )
        create_video_with_frames(
            session=db_session,
            collection_id=collection.collection_id,
            video=VideoStub(path="v.mp4", width=10, height=10, duration_s=1.0, fps=1.0),
        )
        samples = DatasetQuery(dataset=collection, session=db_session, sample_class=VideoSample)
        label_input = LightlyStudioYouTubeVISInstanceSegmentationTrackInput(
            session=db_session,
            samples=samples,
        )
        labels = list(label_input.get_labels())

        assert len(labels) == 0
