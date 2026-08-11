"""Example of timed captions from lemonade sentence transcripts.

Loads a single lemonade cooking video, creates captions with temporal spans from a
sentences JSON file, embeds caption text with PE, scores each span against the video
segment embedding, and stores ``caption_segment_match_score`` on each caption sample.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from environs import Env

import lightly_studio as ls
from lightly_studio.core.video.video_dataset import VideoDataset
from lightly_studio.core.video.video_sample import VideoSample
from lightly_studio.database import db_manager
from lightly_studio.dataset import caption_embedding, timed_captions
from lightly_studio.dataset.perception_encoder_embedding_generator import (
    PerceptionEncoderEmbeddingGenerator,
)

DEFAULT_VIDEO_PATH = Path(
    r"C:\Users\horatiu\Downloads\ego-annotate-demo\ego-annotate-demo\clips\lemonade.mp4"
)
DEFAULT_SENTENCES_PATH = Path(
    r"C:\Users\horatiu\Downloads\ego-annotate-demo\ego-annotate-demo\clips\lemonade.sentences.json"
)

# Read environment variables
env = Env()
env.read_env()

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

# Larger PE checkpoint for higher-quality embeddings.
large_embedding_generator = PerceptionEncoderEmbeddingGenerator(model_name="PE-Core-T16-384")
ls.set_default_embedding_model(large_embedding_generator)

video_path = env.path("EXAMPLES_LEMONADE_VIDEO_PATH", DEFAULT_VIDEO_PATH)
sentences_path = env.path("EXAMPLES_LEMONADE_SENTENCES_PATH", DEFAULT_SENTENCES_PATH)

dataset = VideoDataset.create()
dataset.add_videos_from_path(path=video_path, embed=False, embed_frames=False)

# Create captions from sentences, embed text, then one seek pass per video for
# quality scores and caption-segment match scores.
all_caption_ids: list[UUID] = []
captions_by_video: list[tuple[VideoSample, list[UUID]]] = []
for video in dataset:
    caption_ids = timed_captions.add_captions_from_sentences(
        video=video,
        sentences_path=Path(sentences_path),
    )
    all_caption_ids.extend(caption_ids)
    captions_by_video.append((video, caption_ids))

caption_embedding.embed_captions(session=dataset.session, caption_sample_ids=all_caption_ids)

for video, caption_ids in captions_by_video:
    timed_captions.score_timed_captions_for_video(
        video=video,
        caption_ids=caption_ids,
        embedding_generator=large_embedding_generator,
        compute_quality=True,
        embed_video=False,
        interval_buffer_ratio=0.1,
    )
    timed_captions.detect_repeated_captions_for_video(video=video, caption_ids=caption_ids)
    timed_captions.print_timed_captions_summary(
        session=dataset.session,
        video=video,
        caption_ids=caption_ids,
    )

ls.start_gui()
