"""Helpers for splitting video frames into fixed-length sequences."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from uuid import UUID

from lightly_studio.resolvers.video_frame_resolver import VideoFrameInfoRow


def create_sequences(
    frames: Sequence[VideoFrameInfoRow],
    sequence_length: int,
) -> list[tuple[UUID, ...]]:
    """Split frames into non-overlapping sequences of fixed length.

    Videos are processed in the order they first appear in ``frames``. Within a
    video, frames are sorted by frame number. Trailing frames that do not fill
    a complete sequence are dropped.

    Args:
        frames: Candidate video frames.
        sequence_length: Number of frames per sequence. Must be >= 1.

    Returns:
        Sequences of sample ids, each of length ``sequence_length``. Empty if
        none can be formed.

    Raises:
        ValueError: If ``sequence_length`` < 1.
    """
    if sequence_length < 1:
        raise ValueError(f"sequence_length must be >= 1, got {sequence_length}.")

    by_video: dict[UUID, list[VideoFrameInfoRow]] = defaultdict(list)
    for frame in frames:
        by_video[frame.parent_sample_id].append(frame)

    sequences: list[tuple[UUID, ...]] = []
    # Insertion order of `by_video` is first-seen video order from `frames`.
    for video_frames in by_video.values():
        video_frames_sorted = sorted(video_frames, key=lambda frame: frame.frame_number)
        for start_idx in range(0, len(video_frames_sorted), sequence_length):
            chunk = video_frames_sorted[start_idx : start_idx + sequence_length]
            if len(chunk) != sequence_length:
                break
            sequences.append(tuple(frame.sample_id for frame in chunk))
    return sequences
