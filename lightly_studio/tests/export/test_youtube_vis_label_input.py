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
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.collection import CollectionTable, SampleType
from tests.helpers_resolvers import create_collection
from tests.resolvers.video.helpers import VideoStub, create_video_with_frames


class TestLightlyStudioYouTubeVISInstanceSegmentationTrackInput:
    def test_get_categories(
        self,
        db_session: Session,
        video_collection_with_annotations: CollectionTable,
    ) -> None:
        collection = video_collection_with_annotations
        samples = DatasetQuery(dataset=collection, session=db_session, sample_class=VideoSample)
        label_input = LightlyStudioYouTubeVISInstanceSegmentationTrackInput(
            session=db_session,
            samples=samples,
            annotation_types=[AnnotationType.INSTANCE_SEGMENTATION],
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
            annotation_types=[AnnotationType.INSTANCE_SEGMENTATION],
        )
        assert list(label_input.get_categories()) == []

    def test_get_videos(
        self,
        db_session: Session,
        video_collection_with_annotations: CollectionTable,
    ) -> None:
        collection = video_collection_with_annotations
        samples = DatasetQuery(dataset=collection, session=db_session, sample_class=VideoSample)
        label_input = LightlyStudioYouTubeVISInstanceSegmentationTrackInput(
            session=db_session,
            samples=samples,
            annotation_types=[AnnotationType.INSTANCE_SEGMENTATION],
        )
        assert list(label_input.get_videos()) == [
            Video(
                id=1,
                filename=Path("video_001.mp4").name,
                width=3,
                height=2,
                number_of_frames=2,
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
            annotation_types=[AnnotationType.INSTANCE_SEGMENTATION],
        )
        assert list(label_input.get_videos()) == []

    def test_get_labels(
        self,
        db_session: Session,
        video_collection_with_annotations: CollectionTable,
    ) -> None:
        collection = video_collection_with_annotations
        samples = DatasetQuery(dataset=collection, session=db_session, sample_class=VideoSample)
        label_input = LightlyStudioYouTubeVISInstanceSegmentationTrackInput(
            session=db_session,
            samples=samples,
            annotation_types=[AnnotationType.INSTANCE_SEGMENTATION],
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
        assert obj.segmentations[0] is not None
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
            annotation_types=[AnnotationType.INSTANCE_SEGMENTATION],
        )
        labels = list(label_input.get_labels())

        assert len(labels) == 0
