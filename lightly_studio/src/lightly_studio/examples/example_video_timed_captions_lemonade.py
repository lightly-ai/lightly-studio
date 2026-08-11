"""Example of timed captions from lemonade sentence transcripts.

Loads a single lemonade cooking video, creates captions with temporal spans from a
sentences JSON file, embeds caption text with PE, scores each span against the video
segment embedding, and stores ``caption_segment_match_score`` on each caption sample.
"""

from __future__ import annotations

import json
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
    caption_resolver,
    collection_resolver,
    metadata_resolver,
    sample_embedding_resolver,
)
from lightly_studio.vendor.perception_encoder.vision_encoder import pe, transforms

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


DEFAULT_VIDEO_PATH = Path(
    r"C:\Users\horatiu\Downloads\ego-annotate-demo\ego-annotate-demo\clips\lemonade.mp4"
)
DEFAULT_SENTENCES_PATH = Path(
    r"C:\Users\horatiu\Downloads\ego-annotate-demo\ego-annotate-demo\clips\lemonade.sentences.json"
)


def add_captions_from_sentences(video: VideoSample, sentences_path: Path) -> list[UUID]:
    """Create timed captions for a video from a sentences JSON file.

    Expected JSON shape::

        {
          "sentences": [
            {"text": "...", "start": 1.86, "end": 4.1},
            ...
          ]
        }

    Args:
        video: The video sample to attach captions to.
        sentences_path: Path to the sentences JSON file.

    Returns:
        Created caption sample IDs, ordered by start time.
    """
    payload = json.loads(sentences_path.read_text(encoding="utf-8"))
    sentences = payload["sentences"]

    captions = [
        CaptionCreate(
            parent_sample_id=video.sample_id,
            text=sentence["text"],
            start_time_s=float(sentence["start"]),
            end_time_s=float(sentence["end"]),
        )
        for sentence in sentences
    ]
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

video_path = env.path("EXAMPLES_LEMONADE_VIDEO_PATH", DEFAULT_VIDEO_PATH)
sentences_path = env.path("EXAMPLES_LEMONADE_SENTENCES_PATH", DEFAULT_SENTENCES_PATH)

dataset = VideoDataset.create()
dataset.add_videos_from_path(path=video_path, embed=False, embed_frames=False)
dataset.compute_quality_scores()

# Create captions from sentences, embed text, score segments per video.
all_caption_ids: list[UUID] = []
captions_by_video: list[tuple[VideoSample, list[UUID]]] = []
for video in dataset:
    caption_ids = add_captions_from_sentences(video=video, sentences_path=Path(sentences_path))
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

ls.start_gui()
