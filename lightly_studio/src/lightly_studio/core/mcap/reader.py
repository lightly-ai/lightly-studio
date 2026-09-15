"""Reads frame locators out of a local or remote MCAP file."""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from types import TracebackType
from typing import Any, overload

import fsspec
from mcap import reader as mcap_reader
from mcap.records import Channel, Message, Schema
from mcap.summary import Summary

from lightly_studio.core.mcap import decoding, matching, topic_kind, video_keyframe
from lightly_studio.core.mcap.errors import DataNotLoadedError, McapAccessError, TopicNotFoundError
from lightly_studio.core.mcap.matching import MatchFunction
from lightly_studio.core.mcap.topic_kind import TopicKind
from lightly_studio.core.mcap.type_definitions import FrameLocator, TopicInfo
from lightly_studio.type_definitions import PathLike

logger = logging.getLogger(__name__)


class McapFileReader:
    """Reads frame locators out of an indexed MCAP file.

    The reader returns where data is, not the data itself: it never returns decoded
    video frames or point clouds. Message payloads are only read internally, to detect
    video keyframes.

    The file is opened through fsspec, so it can live in local storage or in remote
    object storage. Reading an indexed file only fetches the summary and the chunks a
    call needs, which keeps a remote recording usable without downloading it.

    The reader holds the file open, so use it as a context manager or call `close()`.

    Attributes:
        path: The path or URI of the MCAP file.
    """

    path: str

    def __init__(self, path: PathLike, storage_options: Mapping[str, Any] | None = None) -> None:
        """Opens a local or remote MCAP file for reading.

        Args:
            path: The path or URI of the MCAP file. Every protocol fsspec supports
                works, e.g. `/data/recording.mcap`, `s3://bucket/recording.mcap`, or
                `gs://bucket/recording.mcap`. Remote protocols need the packages of the
                `cloud-storage` extra.
            storage_options: Options for the fsspec filesystem, e.g. credentials, an
                endpoint, or the read cache to use. Local paths need none. Credentials
                can also come from the environment, as `AWS_*` variables do.

        Raises:
            mcap.exceptions.McapError: If the file is not an MCAP file.
            McapAccessError: If the file cannot be read with random access.
        """
        self.path = str(path)
        self._open_file = fsspec.open(self.path, mode="rb", **dict(storage_options or {}))
        try:
            # `OpenFile.open()` needs the `OpenFile` to stay referenced until close.
            self._stream = self._open_file.open()
            if not self._stream.seekable():
                raise McapAccessError(
                    f"MCAP file '{self.path}' cannot be read with random access. Only "
                    "seekable files can be read, so a remote file needs a filesystem "
                    "that supports range requests."
                )
            # Kept, so that a single message can be decoded without a second pass.
            self._decoder_factories = decoding.decoder_factories()
            self._reader = mcap_reader.make_reader(
                self._stream, decoder_factories=self._decoder_factories
            )
        except Exception:
            self._open_file.close()
            raise
        self._topics: list[TopicInfo] | None = None
        self._topics_by_name: dict[str, TopicInfo] | None = None
        self._locators_by_topic: dict[str, list[FrameLocator]] = {}
        self._decoder_by_channel_id: dict[int, Callable[[bytes], Any] | None] = {}

    def close(self) -> None:
        """Closes the MCAP file."""
        self._open_file.close()

    def __enter__(self) -> McapFileReader:
        """Returns the reader itself."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Closes the MCAP file."""
        self.close()

    def load_data_for_topics(
        self,
        topics: Sequence[str],
        start_time_ns: int | None = None,
        end_time_ns: int | None = None,
    ) -> None:
        """Reads several topics in a single pass and caches their frame locators.

        Call this before `get_frame_locators` for the topics it should return. Reading
        the topics together, instead of one at a time, fetches the chunks they share
        only once, because a chunk holds the messages of every topic in a time span.
        Calling this again for a topic replaces its cached locators.

        Args:
            topics: The topics to locate the messages of. A repeated topic is read once.
            start_time_ns: If given, messages logged before this time are skipped.
            end_time_ns: If given, messages logged at or after this time are skipped.

        Raises:
            TopicNotFoundError: If one of the topics is not in the file.
            McapAccessError: If the file has messages but no chunk index to locate them.
        """
        unique_topics = list(dict.fromkeys(topics))
        video_topics = {
            topic
            for topic in unique_topics
            if self._require_topic_info(topic).kind is TopicKind.VIDEO
        }
        self._require_chunk_index()
        locators_by_topic: dict[str, list[FrameLocator]] = {topic: [] for topic in unique_topics}
        keyframe_log_time_ns_by_topic: dict[str, int | None] = dict.fromkeys(video_topics)
        for schema, channel, message in self._reader.iter_messages(
            topics=unique_topics, start_time=start_time_ns, end_time=end_time_ns
        ):
            if channel.topic in video_topics and self._is_keyframe(
                schema=schema, channel=channel, message=message
            ):
                keyframe_log_time_ns_by_topic[channel.topic] = message.log_time
            locators_by_topic[channel.topic].append(
                _frame_locator(
                    schema=schema,
                    channel=channel,
                    message=message,
                    keyframe_log_time_ns=keyframe_log_time_ns_by_topic.get(channel.topic),
                )
            )
        self._locators_by_topic.update(locators_by_topic)

    @overload
    def get_frame_locators(
        self, topic: str, sync_timestamps: None = None, sync_rule: MatchFunction | None = None
    ) -> list[FrameLocator]: ...

    @overload
    def get_frame_locators(
        self, topic: str, sync_timestamps: Sequence[int], sync_rule: MatchFunction | None = None
    ) -> list[FrameLocator | None]: ...

    def get_frame_locators(
        self,
        topic: str,
        sync_timestamps: Sequence[int] | None = None,
        sync_rule: MatchFunction | None = None,
    ) -> list[FrameLocator] | list[FrameLocator | None]:
        """Returns the frame locators cached for a topic.

        Args:
            topic: The topic to return the locators of. Its data must already be
                loaded, with `load_data_for_topics`.
            sync_timestamps: If given, one locator is returned per query timestamp,
                matched against the topic's locators. Omit to return every locator of
                the topic, in ascending log time order.
            sync_rule: Decides which locator matches a query timestamp. Only used
                together with `sync_timestamps`. Defaults to the locator closest in
                time.

        Returns:
            The locators of the topic. With `sync_timestamps`, one entry per query
            timestamp, in the same order, holding the matching locator or `None` for a
            miss.

        Raises:
            DataNotLoadedError: If `load_data_for_topics` was not called for the topic.
        """
        locators = self._require_loaded_locators(topic)
        if sync_timestamps is None:
            return list(locators)
        indices = matching.match_all(
            queries_ns=sync_timestamps,
            candidates_ns=[locator.log_time_ns for locator in locators],
            match=sync_rule,
        )
        return [None if index is None else locators[index] for index in indices]

    def _require_loaded_locators(self, topic: str) -> list[FrameLocator]:
        """Returns the cached locators of a topic.

        Raises:
            DataNotLoadedError: If `load_data_for_topics` was not called for the topic.
        """
        if topic not in self._locators_by_topic:
            raise DataNotLoadedError(
                f"No data loaded for topic '{topic}'. Call `load_data_for_topics` first."
            )
        return self._locators_by_topic[topic]

    def _is_keyframe(self, schema: Schema | None, channel: Channel, message: Message) -> bool:
        """Returns whether a video message holds a keyframe.

        Only this message is decoded, so that a pass over several topics does not pay
        for decoding the payloads of the topics that are not video.

        Args:
            schema: The schema of the channel.
            channel: The channel the message belongs to.
            message: The message to look at.

        Returns:
            Whether the message holds a keyframe. `False` if it cannot be decoded.
        """
        decoder = self._decoder_for(schema=schema, channel=channel)
        if decoder is None:
            return False
        return video_keyframe.is_keyframe_message(decoder(message.data))

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
        for factory in self._decoder_factories:
            decoder = factory.decoder_for(channel.message_encoding, schema)
            if decoder is not None:
                break
        if decoder is None:
            logger.warning(
                "Cannot decode the messages of topic '%s' in '%s'. Its frame locators "
                "carry no keyframe times.",
                channel.topic,
                self.path,
            )
        self._decoder_by_channel_id[channel.id] = decoder
        return decoder

    def _require_topic_info(self, topic: str) -> TopicInfo:
        """Returns the info of a topic.

        Raises:
            TopicNotFoundError: If the topic is not in the file.
        """
        self._get_topics()
        assert self._topics_by_name is not None
        topic_info = self._topics_by_name.get(topic)
        if topic_info is None:
            raise TopicNotFoundError(f"Topic '{topic}' is not in MCAP file '{self.path}'.")
        return topic_info

    def _get_topics(self) -> list[TopicInfo]:
        """Returns the topics of the file, ordered by name.

        A topic can be recorded on more than one channel, which gives one entry per
        channel.
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

    def _require_chunk_index(self) -> None:
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
                f"MCAP file '{self.path}' has messages but no chunk index. Only chunked, "
                "indexed files can be read."
            )

    def _require_summary(self) -> Summary:
        """Returns the summary section of the file.

        Raises:
            McapAccessError: If the file has no summary section.
        """
        summary = self._reader.get_summary()
        if summary is None:
            raise McapAccessError(
                f"MCAP file '{self.path}' has no summary section. Only indexed files can be read."
            )
        return summary


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


def _frame_locator(
    schema: Schema | None,
    channel: Channel,
    message: Message,
    keyframe_log_time_ns: int | None = None,
) -> FrameLocator:
    """Points at a message without carrying its payload."""
    return FrameLocator(
        channel_id=message.channel_id,
        log_time_ns=message.log_time,
        topic=channel.topic,
        keyframe_log_time_ns=keyframe_log_time_ns,
        schema_name=None if schema is None else schema.name,
    )
