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
from lightly_studio.dataset import caption_embedding
from lightly_studio.dataset.caption_segment_matching import (
    CAPTION_SEGMENT_MATCH_SCORE_KEY,
    score_caption_segments,
)
from lightly_studio.dataset.embedding_manager import EmbeddingManagerProvider
from lightly_studio.models.caption import CaptionCreate, CaptionTable
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import (
    caption_resolver,
    collection_resolver,
    metadata_resolver,
    sample_embedding_resolver,
)


def add_captions_from_annotations(video: VideoSample) -> list[UUID]:
    """Mirror the annotations of a video as captions with the same temporal spans.

    Annotations without a temporal span are mirrored as captions without a span.

    Args:
        video: The video sample whose annotations are mirrored.

    Returns:
        Created caption sample IDs, ordered by start time.
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
    captions.append(
            CaptionCreate(
                parent_sample_id=video.sample_id,
                text="the sun shines brightly in the morning shy",
                start_time_s=0.0,
                end_time_s=1.5,
            )
        )
    captions.sort(key=lambda caption: caption.start_time_s if caption.start_time_s else 0.0)


    return caption_resolver.create_many(
        session=video.get_object_session(),
        parent_collection_id=video.collection_id,
        captions=captions,
    )


def score_timed_captions_for_video(video: VideoSample, caption_ids: list[UUID]) -> None:
    """Score timed captions against video segments and write match scores as metadata."""
    session = video.get_object_session()
    captions = caption_resolver.get_by_ids(session=session, sample_ids=caption_ids)
    timed: list[CaptionTable] = [
        caption for caption in captions if caption.temporal_span_details is not None
    ]
    if not timed:
        return

    caption_collection_id = collection_resolver.get_by_name(
        session=session,
        name=SampleType.CAPTION.value.lower(),
        parent_collection_id=video.collection_id,
    )
    assert caption_collection_id is not None

    model_id = EmbeddingManagerProvider.get_embedding_manager().load_or_get_default_model(
        session=session,
        collection_id=caption_collection_id,
    )
    assert model_id is not None

    timed_ids = [caption.sample_id for caption in timed]
    embedding_rows = sample_embedding_resolver.get_by_sample_ids(
        session=session,
        sample_ids=timed_ids,
        embedding_model_id=model_id,
    )
    embedding_by_id = {row.sample_id: row.embedding for row in embedding_rows}

    intervals: list[tuple[float, float]] = []
    caption_embeddings: list[list[float]] = []
    scored_ids: list[UUID] = []
    for caption in timed:
        embedding = embedding_by_id.get(caption.sample_id)
        span = caption.temporal_span_details
        if embedding is None or span is None:
            continue
        intervals.append((span.start_time_s, span.end_time_s))
        caption_embeddings.append(list(embedding))
        scored_ids.append(caption.sample_id)

    if not intervals:
        return

    scores = score_caption_segments(
        video_path=video.file_path_abs,
        intervals=intervals,
        caption_embeddings=caption_embeddings,
    )
    for caption_id, score in zip(scored_ids, scores):
        metadata_resolver.set_value_for_sample(
            session=session,
            sample_id=caption_id,
            key=CAPTION_SEGMENT_MATCH_SCORE_KEY,
            value=score,
        )


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

# Mirror annotations as captions, embed text, score segments per video.
all_caption_ids: list[UUID] = []
captions_by_video: list[tuple[VideoSample, list[UUID]]] = []
for video in dataset:
    caption_ids = add_captions_from_annotations(video=video)
    all_caption_ids.extend(caption_ids)
    captions_by_video.append((video, caption_ids))

caption_embedding.embed_captions(session=dataset.session, caption_sample_ids=all_caption_ids)

for video, caption_ids in captions_by_video:
    score_timed_captions_for_video(video=video, caption_ids=caption_ids)
    captions = caption_resolver.get_by_ids(session=dataset.session, sample_ids=caption_ids)
    print(f"{video.file_name} ({video.duration_s}s): {len(captions)} caption(s)")
    for caption in captions:
        span = caption.temporal_span_details
        time_range = (
            f"{span.start_time_s:.2f}s - {span.end_time_s:.2f}s" if span is not None else "no span"
        )
        match_score = None
        if span is not None:
            match_score = metadata_resolver.get_value_for_sample(
                session=dataset.session,
                sample_id=caption.sample_id,
                key=CAPTION_SEGMENT_MATCH_SCORE_KEY,
            )
        score_text = f", match={match_score:.3f}" if match_score is not None else ""
        print(f"  - [{time_range}] {caption.text}{score_text}")

ls.start_gui()
