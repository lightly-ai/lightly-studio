"""Example of timed captions with match scores and within-video repetition groups.

Loads videos with ActivityNet annotations, mirrors annotations as captions with temporal
spans, embeds caption text with PE, scores each span against the video segment embedding,
and detects repeated actions via caption-text embedding similarity within each video.

Uses a larger Perception Encoder model for improved embedding quality.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import torch
from environs import Env

import lightly_studio as ls
from lightly_studio.core.video.video_dataset import VideoDataset
from lightly_studio.core.video.video_sample import VideoSample
from lightly_studio.database import db_manager
from lightly_studio.dataset import caption_embedding, file_utils
from lightly_studio.dataset.caption_repetition import (
    DEFAULT_SIMILARITY_THRESHOLD,
    REPEATED_CAPTION_GROUP_ID_KEY,
    REPEATED_CAPTION_MAX_SIMILARITY_KEY,
    find_repeated_captions,
    write_caption_repetition_metadata,
)
from lightly_studio.dataset.caption_segment_matching import (
    CAPTION_SEGMENT_MATCH_SCORE_KEY,
    score_caption_segments,
    set_video_caption_match_aggregates,
)
from lightly_studio.dataset.embedding_manager import EmbeddingManagerProvider
from lightly_studio.dataset.env import LIGHTLY_STUDIO_MODEL_CACHE_DIR
from lightly_studio.dataset.perception_encoder_embedding_generator import (
    PerceptionEncoderEmbeddingGenerator,
)
from lightly_studio.models.caption import CaptionCreate, CaptionTable
from lightly_studio.models.collection import SampleType
from lightly_studio.models.embedding_model import EmbeddingModelCreate
from lightly_studio.resolvers import (
    annotation_resolver,
    caption_resolver,
    collection_resolver,
    metadata_resolver,
    sample_embedding_resolver,
)
from lightly_studio.vendor.perception_encoder.vision_encoder import pe, transforms

#LARGE_MODEL_NAME = "PE-Core-L14-336"
#LARGE_MODEL_NAME = "PE-Core-G14-448"
LARGE_MODEL_NAME = "PE-Core-T16-384"


class LargePerceptionEncoderEmbeddingGenerator(PerceptionEncoderEmbeddingGenerator):
    """Perception Encoder generator using a larger checkpoint for better embeddings."""

    def __init__(self, model_name: str = LARGE_MODEL_NAME) -> None:
        self._model_name = model_name

        LIGHTLY_STUDIO_MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._model, model_path = pe.CLIP.from_config(
            name=model_name, pretrained=True, download_dir=LIGHTLY_STUDIO_MODEL_CACHE_DIR
        )
        self._preprocess = transforms.get_image_transform(self._model.image_size)
        self._tokenizer = transforms.get_text_tokenizer(self._model.context_length)

        # Auto select device: CUDA > MPS (Apple Silicon) > CPU
        self._device = torch.device(
            "cuda"
            if torch.cuda.is_available()
            else "mps"
            if torch.backends.mps.is_available()
            else "cpu"
        )
        self._model = self._model.to(self._device)
        self._model_hash = file_utils.get_file_xxhash(Path(model_path))

    def get_embedding_model_input(self, collection_id: UUID) -> EmbeddingModelCreate:
        return EmbeddingModelCreate(
            name=self._model_name,
            embedding_model_hash=self._model_hash,
            embedding_dimension=self._model.output_dim,
            collection_id=collection_id,
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
            text="Man in a gym. he is standing on a knee and then does a jump and lands on his feet.",
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


def score_timed_captions_for_video(
    video: VideoSample,
    caption_ids: list[UUID],
    embedding_generator: PerceptionEncoderEmbeddingGenerator,
) -> None:
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
        duration = span.end_time_s - span.start_time_s
        buffer = 0.1 * duration
        buffered_start = max(0.0, span.start_time_s - buffer)
        buffered_end = span.end_time_s + buffer
        intervals.append((buffered_start, buffered_end))
        caption_embeddings.append(list(embedding))
        scored_ids.append(caption.sample_id)

    if not intervals:
        return

    scores = score_caption_segments(
        video_path=video.file_path_abs,
        intervals=intervals,
        caption_embeddings=caption_embeddings,
        embedding_generator=embedding_generator,
    )
    for caption_id, score in zip(scored_ids, scores):
        metadata_resolver.set_value_for_sample(
            session=session,
            sample_id=caption_id,
            key=CAPTION_SEGMENT_MATCH_SCORE_KEY,
            value=score,
        )
    set_video_caption_match_aggregates(
        session=session,
        video_sample_id=video.sample_id,
        scores=scores,
    )


def detect_repeated_captions_for_video(
    video: VideoSample,
    caption_ids: list[UUID],
    *,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    min_gap_s: float = 0.0,
) -> None:
    """Cluster temporally separated captions with similar text embeddings."""
    session = video.get_object_session()
    captions = caption_resolver.get_by_ids(session=session, sample_ids=caption_ids)
    timed: list[CaptionTable] = [
        caption for caption in captions if caption.temporal_span_details is not None
    ]
    if len(timed) < 2:
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

    if len(intervals) < 2:
        return

    result = find_repeated_captions(
        caption_embeddings=caption_embeddings,
        intervals=intervals,
        similarity_threshold=similarity_threshold,
        min_gap_s=min_gap_s,
    )
    write_caption_repetition_metadata(
        session=session,
        caption_sample_ids=scored_ids,
        video_sample_id=video.sample_id,
        result=result,
        caption_embeddings=caption_embeddings,
    )


# Read environment variables
env = Env()
env.read_env()

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

# Create instance of larger Perception Encoder model for embeddings
large_embedding_generator = LargePerceptionEncoderEmbeddingGenerator()
ls.set_default_embedding_model(large_embedding_generator)

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
dataset.compute_quality_scores()
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
    score_timed_captions_for_video(
        video=video,
        caption_ids=caption_ids,
        embedding_generator=large_embedding_generator,
    )
    detect_repeated_captions_for_video(video=video, caption_ids=caption_ids)
    captions = caption_resolver.get_by_ids(session=dataset.session, sample_ids=caption_ids)
    print(f"{video.file_name} ({video.duration_s}s): {len(captions)} caption(s)")
    for caption in captions:
        span = caption.temporal_span_details
        time_range = (
            f"{span.start_time_s:.2f}s - {span.end_time_s:.2f}s" if span is not None else "no span"
        )
        match_score = None
        group_id = None
        max_sim = None
        if span is not None:
            match_score = metadata_resolver.get_value_for_sample(
                session=dataset.session,
                sample_id=caption.sample_id,
                key=CAPTION_SEGMENT_MATCH_SCORE_KEY,
            )
            group_id = metadata_resolver.get_value_for_sample(
                session=dataset.session,
                sample_id=caption.sample_id,
                key=REPEATED_CAPTION_GROUP_ID_KEY,
            )
            max_sim = metadata_resolver.get_value_for_sample(
                session=dataset.session,
                sample_id=caption.sample_id,
                key=REPEATED_CAPTION_MAX_SIMILARITY_KEY,
            )
        extras: list[str] = []
        if match_score is not None:
            extras.append(f"match={match_score:.3f}")
        if group_id is not None:
            extras.append(f"repeat_group={group_id}")
        if max_sim is not None:
            extras.append(f"max_sim={max_sim:.3f}")
        extra_text = f", {', '.join(extras)}" if extras else ""
        print(f"  - [{time_range}] {caption.text}{extra_text}")

annotation_resolver.delete_annotations(session=dataset.session, annotation_label_ids=None)
ls.start_gui()
