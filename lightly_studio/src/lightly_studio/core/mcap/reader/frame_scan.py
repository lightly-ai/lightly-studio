"""Builds frame locators from one pass over an indexed MCAP file."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import NamedTuple

from mcap.reader import McapReader
from mcap.records import Channel, Message, Schema

from lightly_studio.core.mcap import capture_time, matching, video_keyframe
from lightly_studio.core.mcap.errors import McapAccessError
from lightly_studio.core.mcap.matching import MatchFunction
from lightly_studio.core.mcap.reader import calibration
from lightly_studio.core.mcap.reader.session import ChannelDecoder
from lightly_studio.core.mcap.type_definitions import FrameLocator, StaticTransform

logger = logging.getLogger(__name__)


class TopicScan(NamedTuple):
    """Locators and static transforms collected while reading a file once."""

    locators_by_topic: dict[str, list[FrameLocator]]
    static_transforms: list[StaticTransform]


class TopicScanRequest(NamedTuple):
    """The topics and time range of one indexing pass."""

    topics: Sequence[str]
    video_topics: set[str]
    start_time_ns: int | None
    end_time_ns: int | None
    static_transform_topic: str | None


class FrameScanner:
    """Reads frame locators in one pass over an open MCAP file."""

    def __init__(self, mcap_reader: McapReader, decoder: ChannelDecoder, path: str) -> None:
        """Binds the scan to one open file.

        Args:
            mcap_reader: The seeking reader of the open file.
            decoder: Decodes a payload, or skips a message that cannot be decoded.
            path: The path or URI of the MCAP file, used in skip warnings.
        """
        self._mcap_reader = mcap_reader
        self._decoder = decoder
        self._path = path

    def scan_topics(self, request: TopicScanRequest) -> TopicScan:
        """Reads frame locators, and optional static transforms, in one pass.

        Args:
            request: The topics to locate and the optional static transform topic
                to collect in the same pass.

        Returns:
            The locators of each topic, in log time order, and the static transforms
            when a static transform topic was given.
        """
        locators_by_topic: dict[str, list[FrameLocator]] = {topic: [] for topic in request.topics}
        keyframe_log_time_ns_by_topic: dict[str, int | None] = dict.fromkeys(request.video_topics)
        static_transforms: list[StaticTransform] = []
        read_topics = [
            *request.topics,
            *([request.static_transform_topic] if request.static_transform_topic else []),
        ]
        for schema, channel, message in self._mcap_reader.iter_messages(
            topics=read_topics, start_time=request.start_time_ns, end_time=request.end_time_ns
        ):
            if channel.topic == request.static_transform_topic:
                static_transforms.extend(
                    calibration.transforms_of_message(
                        decoder=self._decoder,
                        path=self._path,
                        schema=schema,
                        channel=channel,
                        message=message,
                    )
                )
            if channel.topic not in locators_by_topic:
                continue
            locator = self._locator_for_message(
                schema=schema,
                channel=channel,
                message=message,
                video_topics=request.video_topics,
                keyframe_log_time_ns_by_topic=keyframe_log_time_ns_by_topic,
            )
            if locator is not None:
                locators_by_topic[channel.topic].append(locator)
        return TopicScan(locators_by_topic=locators_by_topic, static_transforms=static_transforms)

    def _locator_for_message(
        self,
        schema: Schema | None,
        channel: Channel,
        message: Message,
        video_topics: set[str],
        keyframe_log_time_ns_by_topic: dict[str, int | None],
    ) -> FrameLocator | None:
        """Builds a locator from a message, or `None` if its capture time cannot be read."""
        decoded_message = self._decoder.decoded_payload(
            schema=schema, channel=channel, message=message
        )
        if decoded_message is None:
            return None
        try:
            capture_timestamp_ns = capture_time.from_decoded_message(decoded_message)
        except McapAccessError:
            logger.warning(
                "Cannot read the capture timestamp of a message of topic '%s' in '%s'.",
                channel.topic,
                self._path,
            )
            return None
        if channel.topic in video_topics and video_keyframe.is_keyframe_message(decoded_message):
            keyframe_log_time_ns_by_topic[channel.topic] = message.log_time
        return _frame_locator(
            schema=schema,
            channel=channel,
            message=message,
            capture_timestamp_ns=capture_timestamp_ns,
            keyframe_log_time_ns=keyframe_log_time_ns_by_topic.get(channel.topic),
        )


def sync_locators(
    locators: Sequence[FrameLocator],
    queries_ns: Sequence[int],
    fallback_queries_ns: Sequence[int] | None,
    match: MatchFunction | None,
    topic: str,
) -> list[FrameLocator | None]:
    """Pair queries to locators by capture time, then by log time for misses."""
    if fallback_queries_ns is None:
        ordered = sorted(locators, key=lambda locator: locator.capture_timestamp_ns)
        indices = matching.match_all(
            queries_ns=queries_ns,
            candidates_ns=[locator.capture_timestamp_ns for locator in ordered],
            match=match,
        )
        return [None if index is None else ordered[index] for index in indices]

    matched = matching.match_all_with_fallback(
        primary_queries_ns=queries_ns,
        primary_candidates_ns=[locator.capture_timestamp_ns for locator in locators],
        fallback_queries_ns=fallback_queries_ns,
        fallback_candidates_ns=[locator.log_time_ns for locator in locators],
        match=match,
    )
    if matched.n_fallback:
        logger.warning(
            "Paired %d of %d messages of topic '%s' by log time; capture timestamps did not match.",
            matched.n_fallback,
            len(queries_ns),
            topic,
        )
    return [None if index is None else locators[index] for index in matched.indices]


def _frame_locator(
    schema: Schema | None,
    channel: Channel,
    message: Message,
    capture_timestamp_ns: int,
    keyframe_log_time_ns: int | None = None,
) -> FrameLocator:
    """Points at a message without carrying its payload."""
    return FrameLocator(
        channel_id=message.channel_id,
        log_time_ns=message.log_time,
        capture_timestamp_ns=capture_timestamp_ns,
        topic=channel.topic,
        keyframe_log_time_ns=keyframe_log_time_ns,
        schema_name=None if schema is None else schema.name,
    )
