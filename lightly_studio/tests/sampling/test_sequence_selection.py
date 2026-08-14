"""Unit tests for video sequence selection helpers."""

from __future__ import annotations

from uuid import uuid4

import pytest

from lightly_studio.resolvers.video_frame_resolver import VideoFrameInfoRow
from lightly_studio.sampling import sequence_selection


def test_create_sequences__chunks_and_drops_partial_tail() -> None:
    """Full-length chunks are kept; trailing partial chunks are dropped."""
    video_id = uuid4()
    frames = [
        VideoFrameInfoRow(sample_id=uuid4(), parent_sample_id=video_id, frame_number=i)
        for i in range(12)
    ]

    sequences = sequence_selection.create_sequences(frames=frames, sequence_length=5)

    assert sequences == [
        [frame.sample_id for frame in frames[0:5]],
        [frame.sample_id for frame in frames[5:10]],
    ]


def test_create_sequences__groups_by_video() -> None:
    """Frames from different videos are chunked independently."""
    video_a = uuid4()
    video_b = uuid4()
    ids_a = [uuid4() for _ in range(4)]
    ids_b = [uuid4() for _ in range(4)]
    frames = [
        VideoFrameInfoRow(sample_id=sample_id, parent_sample_id=video_a, frame_number=i)
        for i, sample_id in enumerate(ids_a)
    ] + [
        VideoFrameInfoRow(sample_id=sample_id, parent_sample_id=video_b, frame_number=i)
        for i, sample_id in enumerate(ids_b)
    ]

    sequences = sequence_selection.create_sequences(frames=frames, sequence_length=2)

    assert sequences == [
        [ids_a[0], ids_a[1]],
        [ids_a[2], ids_a[3]],
        [ids_b[0], ids_b[1]],
        [ids_b[2], ids_b[3]],
    ]


def test_create_sequences__returns_empty_when_too_short() -> None:
    """Return empty when no complete sequence exists."""
    video_id = uuid4()
    frames = [
        VideoFrameInfoRow(sample_id=uuid4(), parent_sample_id=video_id, frame_number=i)
        for i in range(3)
    ]

    assert sequence_selection.create_sequences(frames=frames, sequence_length=5) == []


def test_create_sequences__rejects_invalid_length() -> None:
    """sequence_length must be >= 1."""
    with pytest.raises(ValueError, match="sequence_length must be >= 1"):
        sequence_selection.create_sequences(frames=[], sequence_length=0)
