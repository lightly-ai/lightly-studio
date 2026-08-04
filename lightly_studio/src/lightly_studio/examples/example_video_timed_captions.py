"""Example of adding captions with temporal spans to videos.

Loads videos together with their ActivityNet annotations and mirrors every annotation as a
caption: the annotation label becomes the caption text and the annotation's temporal span
becomes the caption's span. Useful to exercise the caption segment UI.
"""

from __future__ import annotations

from environs import Env

import lightly_studio as ls
from lightly_studio.core.video.video_dataset import VideoDataset
from lightly_studio.core.video.video_sample import VideoSample
from lightly_studio.database import db_manager
from lightly_studio.models.caption import CaptionCreate
from lightly_studio.resolvers import caption_resolver


def add_captions_from_annotations(video: VideoSample) -> list[CaptionCreate]:
    """Mirror the annotations of a video as captions with the same temporal spans.

    Annotations without a temporal span are mirrored as captions without a span.

    Args:
        video: The video sample whose annotations are mirrored.

    Returns:
        The created captions, ordered by start time.
    """
    captions = []
    for annotation in video.annotations:
        span = annotation.annotation_base.temporal_span_details
        captions.append(
            CaptionCreate(
                parent_sample_id=video.sample_id,
                text=annotation.class_name,
                start_time_s=span.start_time_s if span is not None else None,
                end_time_s=span.end_time_s if span is not None else None,
            )
        )
    captions.sort(key=lambda caption: caption.start_time_s if caption.start_time_s else 0.0)

    caption_resolver.create_many(
        session=video.get_object_session(),
        parent_collection_id=video.collection_id,
        captions=captions,
    )
    return captions


# Read environment variables
env = Env()
env.read_env()

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

videos_path = env.path(
    "EXAMPLES_ACTIVITYNET_VIDEOS_PATH",
    "dataset_examples/activitynet_10_videos/videos",
)
annotations_path = env.path(
    "EXAMPLES_ACTIVITYNET_JSON_PATH",
    "dataset_examples/activitynet_10_videos/activity_net.v1-3.min.json",
)

dataset = VideoDataset.create()
dataset.add_videos_from_path(path=videos_path, embed=True, embed_frames=False, target_fps=1)
dataset.add_annotations_from_activitynet(
    annotations_json=annotations_path,
    annotation_source="activitynet",
)

# Mirror the loaded annotations as captions and print them per video.
for video in dataset:
    created_captions = add_captions_from_annotations(video=video)
    print(f"{video.file_name} ({video.duration_s}s): {len(created_captions)} caption(s)")
    for caption in created_captions:
        time_range = (
            f"{caption.start_time_s:.2f}s - {caption.end_time_s:.2f}s"
            if caption.start_time_s is not None and caption.end_time_s is not None
            else "no span"
        )
        print(f"  - [{time_range}] {caption.text}")

ls.start_gui()
