from __future__ import annotations

from mcap.records import Channel, ChunkIndex
from mcap.summary import Summary

from lightly_studio.core.mcap.reader import session
from lightly_studio.core.mcap.reader.range_cache import ByteRange

_CAMERA_CHANNEL_ID = 1
_LIDAR_CHANNEL_ID = 2


def test_chunk_ranges() -> None:
    summary = _summary(
        chunk_indexes=[
            _chunk_index(offset=100, length=10, start_ns=0, end_ns=9, channel_ids=[1, 2]),
            _chunk_index(offset=110, length=20, start_ns=10, end_ns=19, channel_ids=[1, 2]),
            _chunk_index(offset=130, length=30, start_ns=20, end_ns=29, channel_ids=[1, 2]),
        ]
    )

    ranges = session.chunk_ranges(
        summary=summary, topics=["/camera"], start_time_ns=12, end_time_ns=20
    )

    assert ranges == [ByteRange(offset=110, length=20), ByteRange(offset=130, length=30)]


def test_chunk_ranges__skips_chunks_without_the_topics() -> None:
    summary = _summary(
        chunk_indexes=[
            _chunk_index(offset=100, length=10, start_ns=0, end_ns=9, channel_ids=[1]),
            _chunk_index(offset=110, length=20, start_ns=0, end_ns=9, channel_ids=[2]),
        ]
    )

    ranges = session.chunk_ranges(
        summary=summary, topics=["/lidar"], start_time_ns=0, end_time_ns=9
    )

    assert ranges == [ByteRange(offset=110, length=20)]


def test_chunk_ranges__keeps_chunks_without_message_indexes() -> None:
    summary = _summary(
        chunk_indexes=[_chunk_index(offset=100, length=10, start_ns=0, end_ns=9, channel_ids=[])]
    )

    ranges = session.chunk_ranges(
        summary=summary, topics=["/lidar"], start_time_ns=0, end_time_ns=9
    )

    assert ranges == [ByteRange(offset=100, length=10)]


def test_chunk_ranges__no_summary() -> None:
    ranges = session.chunk_ranges(summary=None, topics=["/lidar"], start_time_ns=0, end_time_ns=9)

    assert ranges == []


def _summary(chunk_indexes: list[ChunkIndex]) -> Summary:
    summary = Summary()
    summary.channels = {
        _CAMERA_CHANNEL_ID: _channel(channel_id=_CAMERA_CHANNEL_ID, topic="/camera"),
        _LIDAR_CHANNEL_ID: _channel(channel_id=_LIDAR_CHANNEL_ID, topic="/lidar"),
    }
    summary.chunk_indexes = chunk_indexes
    return summary


def _channel(channel_id: int, topic: str) -> Channel:
    return Channel(id=channel_id, topic=topic, message_encoding="json", metadata={}, schema_id=0)


def _chunk_index(
    offset: int, length: int, start_ns: int, end_ns: int, channel_ids: list[int]
) -> ChunkIndex:
    return ChunkIndex(
        chunk_length=length,
        chunk_start_offset=offset,
        compression="",
        compressed_size=length,
        message_end_time=end_ns,
        message_index_length=0,
        message_index_offsets=dict.fromkeys(channel_ids, 0),
        message_start_time=start_ns,
        uncompressed_size=length,
    )
