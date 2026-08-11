"""Example of timed captions with segment-caption match scores.

Loads videos with ActivityNet annotations, mirrors annotations as captions with temporal
spans, embeds caption text with PE, scores each span against the video segment embedding,
and stores ``caption_segment_match_score`` on each caption sample.
"""

from __future__ import annotations

from uuid import UUID

from environs import Env

import lightly_studio as ls
from lightly_studio.core.video.video_dataset import VideoDataset
from lightly_studio.core.video.video_sample import VideoSample
from lightly_studio.database import db_manager
from lightly_studio.dataset import caption_embedding, timed_captions
from lightly_studio.resolvers import annotation_resolver

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
dataset.add_videos_from_path(path=videos_path, embed=False, embed_frames=False)
dataset.add_annotations_from_activitynet(
    annotations_json=annotations_path,
    annotation_source="activitynet",
)

# Mirror annotations as captions, embed text, then one seek pass per video for
# quality scores, whole-video embeddings, and caption-segment match scores.
all_caption_ids: list[UUID] = []
captions_by_video: list[tuple[VideoSample, list[UUID]]] = []
for video in dataset:
    caption_ids = timed_captions.add_captions_from_annotations(video=video)
    all_caption_ids.extend(caption_ids)
    captions_by_video.append((video, caption_ids))

caption_embedding.embed_captions(session=dataset.session, caption_sample_ids=all_caption_ids)

for video, caption_ids in captions_by_video:
    timed_captions.score_timed_captions_for_video(
        video=video,
        caption_ids=caption_ids,
        compute_quality=True,
        embed_video=True,
    )
    timed_captions.detect_repeated_captions_for_video(video=video, caption_ids=caption_ids)
    timed_captions.print_timed_captions_summary(
        session=dataset.session,
        video=video,
        caption_ids=caption_ids,
    )

annotation_resolver.delete_annotations(session=dataset.session, annotation_label_ids=None)
ls.start_gui()
