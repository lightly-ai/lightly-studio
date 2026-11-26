"""End-to-end demonstration of indexing video with annotations in YouTube-VIS format."""

from __future__ import annotations

from pathlib import Path

import e2e_fixture

from lightly_studio.core.annotation.annotation_create import (
    CreateClassification,
    CreateObjectDetection,
)
from lightly_studio.core.dataset_query import OrderByField, VideoFrameSampleField
from lightly_studio.core.video.video_dataset import VideoDataset
from lightly_studio.models.annotation.annotation_base import AnnotationType


def seed() -> None:
    """Create the video E2E fixture."""
    _create_video_query_dataset()
    # The GUI opens the most recently created root collection.
    _create_youtube_vis_dataset()


def _create_video_query_dataset() -> None:
    # Add detections to the same frame in one video and separate frames in the other.
    query_dataset = VideoDataset.create(name="video-query-fixture")
    person = CreateObjectDetection(class_name="person", x=10, y=10, width=20, height=20)
    car = CreateObjectDetection(class_name="car", x=40, y=10, width=20, height=20)
    same_frame_video = "0a275e7f12.mp4"
    separate_frames_video = "0a2f2bd294.mp4"
    for file_name, car_frame in [(same_frame_video, 0), (separate_frames_video, 1)]:
        query_dataset.add_videos_from_path(
            path=Path("datasets/youtube_vis_50_videos/train/videos") / file_name,
            embed=False,
            embed_frames=False,
        )
        frames = (
            query_dataset.frames()
            .match(VideoFrameSampleField.parent_video.file_name == file_name)
            .order_by(OrderByField(VideoFrameSampleField.frame_number))[:2]
            .to_list()
        )
        frames[0].add_annotation(annotation=person, annotation_source="query-fixture")
        frames[car_frame].add_annotation(annotation=car, annotation_source="query-fixture")

        if file_name == separate_frames_video:
            frames[0].parent_video.add_annotation(
                annotation=CreateClassification(class_name="run"), annotation_source="query-fixture"
            )

    query_dataset.add_annotations_from_activitynet(
        annotations_json=Path(__file__).with_name("query_events.json"),
        annotation_source="query-fixture",
    )


def _create_youtube_vis_dataset() -> None:
    dataset = VideoDataset.create()
    dataset.add_videos_from_youtube_vis(
        annotations_json="datasets/youtube_vis_50_videos/train/instances_50.json",
        videos_path="datasets/youtube_vis_50_videos/train/videos",
        annotation_type=AnnotationType.SEGMENTATION_MASK,
        embed=False,
    )


if __name__ == "__main__":
    e2e_fixture.run(seed=seed)
