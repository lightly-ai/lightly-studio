"""Reads frame locators out of a local or remote MCAP file."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from types import TracebackType
from typing import Any, overload

import fsspec
from mcap import reader as mcap_reader
from mcap.records import Channel, Message, Schema
from mcap.summary import Summary

from lightly_studio.core.mcap import matching, topic_kind
from lightly_studio.core.mcap.errors import DataNotLoadedError, McapAccessError, TopicNotFoundError
from lightly_studio.core.mcap.matching import MatchFunction
from lightly_studio.core.mcap.type_definitions import FrameLocator, TopicInfo
from lightly_studio.type_definitions import PathLike


class McapFileReader:
    """Reads frame locators out of an indexed MCAP file.

    The reader returns where data is, not the data itself: it never returns decoded
    video frames or point clouds, and it does not read message payloads.

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
            self._reader = mcap_reader.make_reader(self._stream)
        except Exception:
            self._open_file.close()
            raise
        self._topics: list[TopicInfo] | None = None
        self._topic_names: set[str] | None = None
        self._locators_by_topic: dict[str, list[FrameLocator]] = {}

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
        """
        unique_topics = list(dict.fromkeys(topics))
        for topic in unique_topics:
            self._require_topic(topic)
        locators_by_topic: dict[str, list[FrameLocator]] = {topic: [] for topic in unique_topics}
        for schema, channel, message in self._reader.iter_messages(
            topics=unique_topics, start_time=start_time_ns, end_time=end_time_ns
        ):
            locators_by_topic[channel.topic].append(
                _frame_locator(schema=schema, channel=channel, message=message)
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

    def _require_topic(self, topic: str) -> None:
        """Checks that a topic is in the file.

        Raises:
            TopicNotFoundError: If the topic is not in the file.
        """
        self._get_topics()
        assert self._topic_names is not None
        if topic not in self._topic_names:
            raise TopicNotFoundError(f"Topic '{topic}' is not in MCAP file '{self.path}'.")

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
            self._topic_names = {topic.name for topic in self._topics}
        return self._topics

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


def _frame_locator(schema: Schema | None, channel: Channel, message: Message) -> FrameLocator:
    """Points at a message without carrying its payload."""
    return FrameLocator(
        channel_id=message.channel_id,
        log_time_ns=message.log_time,
        topic=channel.topic,
        schema_name=None if schema is None else schema.name,
    )
