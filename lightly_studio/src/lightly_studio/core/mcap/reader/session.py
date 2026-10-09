"""Opens an indexed MCAP file and reads its summary."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator, Mapping, Sequence
from enum import Enum
from typing import IO, Any

import fsspec
from mcap import reader as mcap_reader
from mcap.decoder import DecoderFactory
from mcap.exceptions import DecoderNotFoundError
from mcap.reader import McapReader
from mcap.records import Channel, Message, Schema
from mcap.summary import Summary

from lightly_studio.core.mcap import decoding, topic_kind
from lightly_studio.core.mcap.errors import (
    ChannelNotFoundError,
    McapAccessError,
    TopicNotFoundError,
)
from lightly_studio.core.mcap.type_definitions import TopicInfo

logger = logging.getLogger(__name__)

# The fsspec read cache of a reader opened for random access. A small block keeps the
# first read small, because a filesystem fetches a whole block for every read that
# misses the cache, and the default block of a remote filesystem is tens of megabytes.
_RANDOM_READ_CACHE_TYPE = "readahead"
_RANDOM_READ_BLOCK_SIZE_BYTES = 64 * 1024


class ReadPattern(Enum):
    """How much data the reader fetches ahead of a read.

    Attributes:
        SEQUENTIAL: Fetches the large blocks the filesystem uses by default. Use it to
            read a whole recording, e.g. to index it.
        RANDOM: Fetches small blocks. Use it to open a remote file and read a few
            messages, e.g. to serve a single frame, where the time to the first byte
            matters more than the throughput.
    """

    SEQUENTIAL = "sequential"
    RANDOM = "random"


class ChannelDecoder:
    """Decodes channel payloads, and remembers a channel that cannot be decoded."""

    def __init__(self, path: str, factories: Sequence[DecoderFactory]) -> None:
        """Caches one decoder per channel.

        Args:
            path: The path or URI of the MCAP file, used in skip warnings.
            factories: The decoder factories registered for the file.
        """
        self._path = path
        self._factories = factories
        self._decoder_by_channel_id: dict[int, Callable[[bytes], Any] | None] = {}

    def decoded_payload(
        self, schema: Schema | None, channel: Channel, message: Message
    ) -> Any | None:
        """Decodes a message payload, or `None` if it cannot be decoded."""
        decoder = self._decoder_for(schema=schema, channel=channel)
        if decoder is None:
            return None
        try:
            return decoder(message.data)
        except Exception:
            logger.warning(
                "Cannot decode a message of topic '%s' in '%s'. It is skipped.",
                channel.topic,
                self._path,
            )
            return None

    def _decoder_for(
        self, schema: Schema | None, channel: Channel
    ) -> Callable[[bytes], Any] | None:
        """Returns the decoder of a channel, or `None` if no factory can decode it.

        The lookup is cached per channel, and a channel that cannot be decoded is
        reported once.
        """
        if channel.id in self._decoder_by_channel_id:
            return self._decoder_by_channel_id[channel.id]

        decoder: Callable[[bytes], Any] | None = None
        for factory in self._factories:
            decoder = factory.decoder_for(message_encoding=channel.message_encoding, schema=schema)
            if decoder is not None:
                break
        if decoder is None:
            logger.warning(
                "Cannot decode the messages of topic '%s' in '%s'. Its messages are skipped.",
                channel.topic,
                self._path,
            )
        self._decoder_by_channel_id[channel.id] = decoder
        return decoder


class TopicIndex:
    """The topics and chunk index recorded in an MCAP summary."""

    def __init__(self, path: str, mcap_reader: McapReader) -> None:
        """Reads topics from the summary the first time they are asked for.

        Args:
            path: The path or URI of the MCAP file, used in error messages.
            mcap_reader: The seeking reader of the open file.
        """
        self._path = path
        self._mcap_reader = mcap_reader
        self._topics: list[TopicInfo] | None = None
        self._topics_by_name: dict[str, TopicInfo] | None = None

    def topics(self) -> list[TopicInfo]:
        """Returns the topics of the file, ordered by name.

        A topic can be recorded on more than one channel, which gives one entry per
        channel. Reading the topics only reads the file's summary section (footer and
        summary, not the message chunks), so it does not require downloading or
        indexing the whole file: a remote file behind a filesystem that supports range
        requests (local disk, S3, GCS, or plain HTTP) is summarized cheaply.
        """
        if self._topics is None:
            summary = self._require_summary()
            message_counts = (
                {} if summary.statistics is None else summary.statistics.channel_message_counts
            )
            topics = [
                _topic_info(
                    channel=channel,
                    schema=summary.schemas.get(channel.schema_id),
                    message_count=message_counts.get(channel.id),
                )
                for channel in summary.channels.values()
            ]
            self._topics = sorted(topics, key=lambda topic: topic.name)
            self._topics_by_name = {}
            for topic_info in self._topics:
                self._topics_by_name.setdefault(topic_info.name, topic_info)
        return self._topics

    def require_topic_info(self, topic: str) -> TopicInfo:
        """Returns the info of a topic.

        Raises:
            TopicNotFoundError: If the topic is not in the file.
        """
        self.topics()
        assert self._topics_by_name is not None
        topic_info = self._topics_by_name.get(topic)
        if topic_info is None:
            raise TopicNotFoundError(f"Topic '{topic}' is not in MCAP file '{self._path}'.")
        return topic_info

    def require_channel_info(self, channel_id: int) -> TopicInfo:
        """Returns the topic info of a channel.

        Raises:
            ChannelNotFoundError: If the channel id is not in the file.
        """
        for topic_info in self.topics():
            if topic_info.channel_id == channel_id:
                return topic_info
        raise ChannelNotFoundError(f"Channel {channel_id} is not in MCAP file '{self._path}'.")

    def has_topic(self, topic: str) -> bool:
        """Returns whether a topic is in the file."""
        self.topics()
        assert self._topics_by_name is not None
        return topic in self._topics_by_name

    def require_chunk_index(self) -> None:
        """Checks that the file's messages, if any, are reachable through a chunk index.

        Without a chunk index, `mcap.reader.SeekingReader.iter_messages` falls back to a
        full, non-seeking scan of the file instead of seeking to the messages a call
        needs. A file with no messages has no chunks either, so it is let through.

        Raises:
            McapAccessError: If the file has messages but no chunk index to locate them.
        """
        summary = self._require_summary()
        if len(summary.chunk_indexes) > 0:
            return
        message_count = 0 if summary.statistics is None else summary.statistics.message_count
        if message_count > 0:
            raise McapAccessError(
                f"MCAP file '{self._path}' has messages but no chunk index. Only chunked, "
                "indexed files can be read."
            )

    def _require_summary(self) -> Summary:
        """Returns the summary section of the file.

        Raises:
            McapAccessError: If the file has no summary section.
        """
        summary = self._mcap_reader.get_summary()
        if summary is None:
            raise McapAccessError(
                f"MCAP file '{self._path}' has no summary section. Only indexed files can be read."
            )
        return summary


def open_reader(
    path: str,
    storage_options: Mapping[str, Any] | None,
    read_pattern: ReadPattern,
) -> tuple[IO[bytes], McapReader, ChannelDecoder]:
    """Opens a local or remote MCAP file for seeking reads.

    Args:
        path: The path or URI of the MCAP file.
        storage_options: Options for the fsspec filesystem, e.g. credentials.
        read_pattern: How much data a read fetches ahead.

    Returns:
        The binary stream, the seeking reader, and the payload decoder. The caller
        closes the stream.

    Raises:
        mcap.exceptions.McapError: If the file is not an MCAP file.
        McapAccessError: If the file cannot be read with random access.
    """
    # The filesystem is opened separately from the file, because the read cache is
    # an argument of `open()`, which `fsspec.open()` does not forward to it.
    filesystem, path_in_filesystem = fsspec.url_to_fs(path, **dict(storage_options or {}))
    stream = filesystem.open(path_in_filesystem, mode="rb", **_read_cache_options(read_pattern))
    try:
        if not stream.seekable():
            raise McapAccessError(
                f"MCAP file '{path}' cannot be read with random access. Only "
                "seekable files can be read, so a remote file needs a filesystem "
                "that supports range requests."
            )
        # Kept, so that a single message can be decoded without a second pass.
        factories = decoding.decoder_factories()
        decoder = ChannelDecoder(path=path, factories=factories)
        reader = mcap_reader.make_reader(stream, decoder_factories=factories)
    except Exception:
        stream.close()
        raise
    return stream, reader, decoder


def iter_decoded_messages(
    mcap_reader: McapReader,
    topics: TopicIndex,
    path: str,
    topic: str,
) -> Iterator[tuple[int, Any]]:
    """Yields the log time and the payload of every decoded message on a topic.

    Raises:
        TopicNotFoundError: If the topic is not in the file.
        McapAccessError: If a message on the topic cannot be decoded, e.g.
            because no decoder factory is registered for its encoding.
    """
    topics.require_topic_info(topic)
    try:
        for _, _, message, decoded_message in mcap_reader.iter_decoded_messages(topics=[topic]):
            yield message.log_time, decoded_message
    except DecoderNotFoundError as error:
        raise McapAccessError(
            f"Cannot decode a message of topic '{topic}' in '{path}': {error}"
        ) from error


def _read_cache_options(read_pattern: ReadPattern) -> dict[str, Any]:
    """Returns the `fsspec` open arguments that give a read pattern its read cache.

    Args:
        read_pattern: The pattern the file is read with.

    Returns:
        The arguments to pass to `AbstractFileSystem.open`. Empty for a sequential
        read, which is what the filesystem defaults are made for.
    """
    if read_pattern is ReadPattern.SEQUENTIAL:
        return {}
    return {
        "cache_type": _RANDOM_READ_CACHE_TYPE,
        "block_size": _RANDOM_READ_BLOCK_SIZE_BYTES,
    }


def _topic_info(channel: Channel, schema: Schema | None, message_count: int | None) -> TopicInfo:
    """Describes the topic a channel carries."""
    schema_name = None if schema is None else schema.name
    return TopicInfo(
        name=channel.topic,
        channel_id=channel.id,
        message_encoding=channel.message_encoding,
        schema_name=schema_name,
        schema_encoding=None if schema is None else schema.encoding,
        kind=topic_kind.from_schema_name(schema_name),
        message_count=message_count,
    )
