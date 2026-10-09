"""Tests for the process-wide video decoder cache."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from pytest_mock import MockerFixture

from lightly_studio.core.mcap.compressed_video import VideoDecoder
from lightly_studio.services.recording_service import video_decoder_cache


@pytest.fixture(autouse=True)
def clear_decoder_cache() -> Iterator[None]:
    video_decoder_cache.clear()
    yield
    video_decoder_cache.clear()


def test_take_decoder__empty() -> None:
    assert video_decoder_cache.take_decoder(uri="a.mcap", channel_id=1) is None


def test_take_decoder__removes_the_decoder() -> None:
    decoder = VideoDecoder(keyframe_log_time_ns=100)
    video_decoder_cache.put_decoder(uri="a.mcap", channel_id=1, decoder=decoder)

    first = video_decoder_cache.take_decoder(uri="a.mcap", channel_id=1)
    second = video_decoder_cache.take_decoder(uri="a.mcap", channel_id=1)

    assert first is decoder
    assert second is None


def test_take_decoder__keyed_by_uri_and_channel() -> None:
    decoder = VideoDecoder(keyframe_log_time_ns=100)
    video_decoder_cache.put_decoder(uri="a.mcap", channel_id=1, decoder=decoder)

    assert video_decoder_cache.take_decoder(uri="a.mcap", channel_id=2) is None
    assert video_decoder_cache.take_decoder(uri="b.mcap", channel_id=1) is None


def test_put_decoder__replaces_the_decoder() -> None:
    first = VideoDecoder(keyframe_log_time_ns=100)
    second = VideoDecoder(keyframe_log_time_ns=200)

    video_decoder_cache.put_decoder(uri="a.mcap", channel_id=1, decoder=first)
    video_decoder_cache.put_decoder(uri="a.mcap", channel_id=1, decoder=second)

    assert video_decoder_cache.take_decoder(uri="a.mcap", channel_id=1) is second


def test_put_decoder__evicts_the_least_recently_stored(mocker: MockerFixture) -> None:
    mocker.patch.object(video_decoder_cache, "_DECODER_CACHE_SIZE", 2)
    decoders = [VideoDecoder(keyframe_log_time_ns=100) for _ in range(3)]

    for channel_id, decoder in enumerate(decoders):
        video_decoder_cache.put_decoder(uri="a.mcap", channel_id=channel_id, decoder=decoder)

    assert video_decoder_cache.take_decoder(uri="a.mcap", channel_id=0) is None
    assert video_decoder_cache.take_decoder(uri="a.mcap", channel_id=1) is decoders[1]
    assert video_decoder_cache.take_decoder(uri="a.mcap", channel_id=2) is decoders[2]


def test_clear() -> None:
    video_decoder_cache.put_decoder(
        uri="a.mcap", channel_id=1, decoder=VideoDecoder(keyframe_log_time_ns=100)
    )

    video_decoder_cache.clear()

    assert video_decoder_cache.take_decoder(uri="a.mcap", channel_id=1) is None
