"""Embed the sequences of an MCAP dataset from frames of their first camera."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from uuid import UUID

from mcap.exceptions import McapError
from PIL.Image import Image
from sqlmodel import Session

from lightly_studio.core.mcap import compressed_video
from lightly_studio.core.mcap.errors import McapAccessError
from lightly_studio.core.mcap.reader import McapFileReader, ReadPattern
from lightly_studio.embed import embed_samples
from lightly_studio.models.mcap_group_sequence import McapSequenceKeyframe
from lightly_studio.resolvers import mcap_group_sequence_resolver, recording_resolver

logger = logging.getLogger(__name__)

FRAMES_PER_SEQUENCE = 32
"""The number of keyframes sampled from a sequence to compute its embedding."""

EMBED_FRAME_MAX_EDGE = 384
"""Long edge of each decoded keyframe before embedding, to bound memory use."""


def embed_mcap_sequences(
    session: Session,
    collection_id: UUID,
    sequence_sample_ids: list[UUID],
    frames_per_sequence: int = FRAMES_PER_SEQUENCE,
) -> None:
    """Embed MCAP sequences and store the embeddings.

    The embedding of a sequence is computed from evenly spaced keyframes of the first
    camera component of the dataset. The keyframes are embedded as images, and the mean of
    their embeddings is the embedding of the sequence.

    Does nothing (and logs a warning) if the dataset has no camera component or no
    image embedder is available. A sequence without a decodable keyframe gets no
    embedding.

    Args:
        session: Database session for resolver operations.
        collection_id: The SEQUENCE collection of the dataset.
        sequence_sample_ids: The sample IDs of the sequences to embed.
        frames_per_sequence: The number of keyframes to sample from each sequence.
            A sequence with fewer keyframes uses all of them.
    """
    if frames_per_sequence <= 0:
        raise ValueError(f"frames_per_sequence must be greater than 0, got {frames_per_sequence}.")
    if not sequence_sample_ids:
        return
    video_frame_collection_id = mcap_group_sequence_resolver.get_first_video_frame_collection_id(
        session=session, sequence_collection_id=collection_id
    )
    if video_frame_collection_id is None:
        logger.warning("The dataset has no camera component. Skipping embedding generation.")
        return
    keyframes_by_sequence = mcap_group_sequence_resolver.get_keyframes(
        session=session,
        sequence_sample_ids=sequence_sample_ids,
        video_frame_collection_id=video_frame_collection_id,
    )

    def load_frames(sequence_sample_id: UUID) -> list[Image]:
        keyframes = sample_keyframes(
            keyframes=keyframes_by_sequence.get(sequence_sample_id, []),
            count=frames_per_sequence,
        )
        if not keyframes:
            return []
        uri = _get_recording_uri(session=session, sequence_sample_id=sequence_sample_id)
        return _load_keyframes(uri=uri, keyframes=keyframes)

    embed_samples.embed_mcap_image_frames(
        session=session,
        collection_id=collection_id,
        sample_ids=sequence_sample_ids,
        load_frames=load_frames,
    )


def sample_keyframes(
    keyframes: Sequence[McapSequenceKeyframe], count: int
) -> list[McapSequenceKeyframe]:
    """Choose evenly spaced keyframes without repetition, in the order of their log time.

    The keyframes ordered by log time are split into `count` runs of equal length, and
    the middle keyframe of each run is chosen.

    Args:
        keyframes: The keyframes to choose from.
        count: The number of keyframes to choose. If there are fewer, all are chosen.

    Returns:
        The chosen keyframes, ordered by log time so that the file is read forward.
    """
    ordered = sorted(keyframes, key=lambda keyframe: keyframe.log_time_ns)
    if count >= len(ordered):
        return ordered
    return [ordered[int((index + 0.5) * len(ordered) / count)] for index in range(count)]


def _get_recording_uri(session: Session, sequence_sample_id: UUID) -> str:
    """Return the URI of the recording of a sequence.

    Raises:
        ValueError: If the sequence or its recording does not exist.
    """
    sequence = mcap_group_sequence_resolver.get_by_id(session=session, sample_id=sequence_sample_id)
    if sequence is None:
        raise ValueError(f"No MCAP sequence found for sample_id: {sequence_sample_id}")
    recording = recording_resolver.get_by_id(session=session, recording_id=sequence.recording_id)
    if recording is None:
        raise ValueError(f"No recording found for recording_id: {sequence.recording_id}")
    return recording.uri


def _load_keyframes(uri: str, keyframes: Sequence[McapSequenceKeyframe]) -> list[Image]:
    """Read and decode keyframes from a recording.

    A keyframe that cannot be read or decoded is left out with a warning. If the
    recording cannot be opened, no frames are returned.

    Returns:
        The decoded images, in the order of `keyframes`.
    """
    images: list[Image] = []
    try:
        with McapFileReader(uri, read_pattern=ReadPattern.RANDOM) as reader:
            for keyframe in keyframes:
                try:
                    message = reader.get_decoded_message_at(
                        channel_id=keyframe.channel_id, timestamp_ns=keyframe.log_time_ns
                    )
                    if message is None:
                        continue
                    images.append(
                        compressed_video.to_image(
                            decoded_message=message.decoded_message,
                            width=EMBED_FRAME_MAX_EDGE,
                        )
                    )
                except McapAccessError as error:
                    logger.warning(
                        "Skipping the frame at %d ns of '%s': %s", keyframe.log_time_ns, uri, error
                    )
    except (OSError, McapError, McapAccessError) as error:
        logger.warning("Cannot read frames of '%s' to embed it: %s", uri, error)
    return images
