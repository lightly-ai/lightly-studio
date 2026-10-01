"""Reads frame locators and calibration out of a local or remote MCAP file."""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from types import TracebackType
from typing import Any, overload

import numpy as np
from mcap.exceptions import DecoderNotFoundError
from numpy.typing import NDArray

from lightly_studio.core.mcap.errors import DataNotLoadedError, McapAccessError
from lightly_studio.core.mcap.matching import MatchFunction
from lightly_studio.core.mcap.reader import calibration, frame_scan, session
from lightly_studio.core.mcap.reader.calibration import STATIC_TRANSFORM_TOPIC
from lightly_studio.core.mcap.reader.frame_scan import FrameScanner, TopicScanRequest
from lightly_studio.core.mcap.reader.session import ReadPattern, TopicIndex
from lightly_studio.core.mcap.topic_kind import TopicKind
from lightly_studio.core.mcap.transforms import TransformTree
from lightly_studio.core.mcap.type_definitions import (
    CameraIntrinsics,
    DecodedMessage,
    FrameLocator,
    StaticTransform,
    TopicInfo,
)
from lightly_studio.type_definitions import PathLike


class McapFileReader:
    """Reads frame locators and calibration out of an indexed MCAP file.

    The reader returns where data is, not the data itself: it never returns decoded
    video frames or point clouds. Message payloads are only read internally, to read
    capture timestamps, detect video keyframes, and read calibration.

    The file is opened through fsspec, so it can live in local storage or in remote
    object storage. Reading an indexed file only fetches the summary and the chunks a
    call needs, which keeps a remote recording usable without downloading it.

    The reader holds the file open, so use it as a context manager or call `close()`.

    Attributes:
        path: The path or URI of the MCAP file.
    """

    path: str

    def __init__(
        self,
        path: PathLike,
        storage_options: Mapping[str, Any] | None = None,
        read_pattern: ReadPattern = ReadPattern.SEQUENTIAL,
    ) -> None:
        """Opens a local or remote MCAP file for reading.

        Args:
            path: The path or URI of the MCAP file. Every protocol fsspec supports
                works, e.g. `/data/recording.mcap`, `s3://bucket/recording.mcap`, or
                `gs://bucket/recording.mcap`. Remote protocols need the packages of the
                `cloud-storage` extra.
            storage_options: Options for the fsspec filesystem, e.g. credentials, an
                endpoint, or the read cache to use. Local paths need none. Credentials
                can also come from the environment, as `AWS_*` variables do.
            read_pattern: How much data a read fetches ahead. Defaults to reading a
                whole recording. Pass `ReadPattern.RANDOM` to open a remote file and
                read only a few messages from it.

        Raises:
            mcap.exceptions.McapError: If the file is not an MCAP file.
            McapAccessError: If the file cannot be read with random access.
        """
        self.path = str(path)
        self._stream, self._reader, self._decoder = session.open_reader(
            path=self.path, storage_options=storage_options, read_pattern=read_pattern
        )
        self._topic_index = TopicIndex(path=self.path, mcap_reader=self._reader)
        self._locators_by_topic: dict[str, list[FrameLocator]] = {}
        self._intrinsics_by_topic: dict[str, CameraIntrinsics] = {}
        self._transform_tree_by_topic: dict[str, TransformTree] = {}
        self._static_transforms_by_topic: dict[str, list[StaticTransform]] = {}

    def close(self) -> None:
        """Closes the MCAP file."""
        self._stream.close()

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
        static_transform_topic: str | None = None,
    ) -> None:
        """Reads several topics in a single pass and caches their frame locators.

        Call this before `get_frame_locators` for the topics it should return. Reading
        the topics together, instead of one at a time, fetches the chunks they share
        only once, because a chunk holds the messages of every topic in a time span.
        Calling this again for a topic replaces its cached locators.

        Each locator stores the MCAP log time, to seek the payload, and the capture
        timestamp from the message header. A message that cannot be decoded, or that
        has no header stamp, is skipped.

        Args:
            topics: The topics to locate the messages of. A repeated topic is read once.
            start_time_ns: If given, messages logged before this time are skipped.
            end_time_ns: If given, messages logged at or after this time are skipped.
            static_transform_topic: If given, the transforms of this topic are read in
                the same pass and cached for `get_static_transforms`. Only the
                transforms logged in the time range are read. A topic that is not in
                the file caches no transforms.

        Raises:
            TopicNotFoundError: If one of the topics is not in the file.
            McapAccessError: If the file has messages but no chunk index to locate them.
        """
        unique_topics = list(dict.fromkeys(topics))
        video_topics = {
            topic
            for topic in unique_topics
            if self._topic_index.require_topic_info(topic).kind is TopicKind.VIDEO
        }
        self._topic_index.require_chunk_index()
        scan = FrameScanner(
            mcap_reader=self._reader, decoder=self._decoder, path=self.path
        ).scan_topics(
            request=TopicScanRequest(
                topics=unique_topics,
                video_topics=video_topics,
                start_time_ns=start_time_ns,
                end_time_ns=end_time_ns,
                static_transform_topic=static_transform_topic,
            )
        )
        self._locators_by_topic.update(scan.locators_by_topic)
        if static_transform_topic:
            self._static_transforms_by_topic[static_transform_topic] = scan.static_transforms

    @overload
    def get_frame_locators(
        self,
        topic: str,
        sync_timestamps: None = None,
        sync_rule: MatchFunction | None = None,
        fallback_timestamps: None = None,
    ) -> list[FrameLocator]: ...

    @overload
    def get_frame_locators(
        self,
        topic: str,
        sync_timestamps: Sequence[int],
        sync_rule: MatchFunction | None = None,
        fallback_timestamps: Sequence[int] | None = None,
    ) -> list[FrameLocator | None]: ...

    def get_frame_locators(
        self,
        topic: str,
        sync_timestamps: Sequence[int] | None = None,
        sync_rule: MatchFunction | None = None,
        fallback_timestamps: Sequence[int] | None = None,
    ) -> list[FrameLocator] | list[FrameLocator | None]:
        """Returns the frame locators cached for a topic.

        Args:
            topic: The topic to return the locators of. Its data must already be
                loaded, with `load_data_for_topics`.
            sync_timestamps: If given, one locator is returned per query timestamp,
                matched against the capture timestamps of the topic's locators. Omit to
                return every locator of the topic, in ascending log time order.
            sync_rule: Decides which locator matches a query timestamp. Only used
                together with `sync_timestamps`. Defaults to the locator closest in
                capture time.
            fallback_timestamps: If given with `sync_timestamps`, a capture miss is
                retried against the locators' log times. Same length as
                `sync_timestamps`. Use the query log times here when capture clocks
                do not overlap, e.g. a camera timestamp on a device clock.

        Returns:
            The locators of the topic. With `sync_timestamps`, one entry per query
            timestamp, in the same order, holding the matching locator or `None` for a
            miss.

        Raises:
            DataNotLoadedError: If `load_data_for_topics` was not called for the topic.
            ValueError: If `fallback_timestamps` is given without `sync_timestamps`, or
                the two lists have different lengths.
        """
        locators = self._require_loaded_locators(topic)
        if sync_timestamps is None:
            if fallback_timestamps is not None:
                raise ValueError("fallback_timestamps requires sync_timestamps.")
            return list(locators)
        return frame_scan.sync_locators(
            locators=locators,
            queries_ns=sync_timestamps,
            fallback_queries_ns=fallback_timestamps,
            match=sync_rule,
            topic=topic,
        )

    def get_intrinsic(self, topic: str) -> CameraIntrinsics:
        """Returns the camera intrinsics recorded on a camera info topic.

        Intrinsics are static, so the first message on the topic is used. The result
        is cached, so repeated calls for the same topic read the file only once.

        Args:
            topic: The camera info topic, e.g. `/cam/front/camera_info`.

        Returns:
            The intrinsics of the camera.

        Raises:
            TopicNotFoundError: If the topic is not in the file.
            McapAccessError: If the topic has no message, if its messages do not hold
                camera intrinsics, or if its messages cannot be decoded.
        """
        if topic not in self._intrinsics_by_topic:
            self._intrinsics_by_topic[topic] = calibration.read_intrinsic(
                messages=self.iter_decoded_messages(topic), topic=topic
            )
        return self._intrinsics_by_topic[topic]

    def get_static_transform(
        self,
        parent_frame_id: str,
        child_frame_id: str,
        topic: str = STATIC_TRANSFORM_TOPIC,
    ) -> NDArray[np.float64]:
        """Returns the static transform between two coordinate frames.

        Args:
            parent_frame_id: The frame to map points to, e.g. the camera frame.
            child_frame_id: The frame to map points from, e.g. the lidar frame.
            topic: The topic the static transforms are published on.

        Returns:
            The 4x4 homogeneous transform that maps points from the child frame to the
            parent frame.

        Raises:
            TopicNotFoundError: If the topic is not in the file.
            TransformNotFoundError: If no chain of transforms connects the two frames.
            McapAccessError: If a message on the topic cannot be decoded.
        """
        if topic not in self._transform_tree_by_topic:
            self._transform_tree_by_topic[topic] = TransformTree(
                calibration.read_static_transforms(messages=self.iter_decoded_messages(topic))
            )
        return self._transform_tree_by_topic[topic].lookup(
            target_frame_id=parent_frame_id, source_frame_id=child_frame_id
        )

    def get_static_transforms(self, topic: str = STATIC_TRANSFORM_TOPIC) -> list[StaticTransform]:
        """Returns the static transforms published on a topic.

        A topic that is not in the file counts as a topic without transforms. The
        result is cached for the lifetime of the reader. The topic is read only if
        `load_data_for_topics` did not read it already. Indexing stores these edges.

        Args:
            topic: The topic the static transforms are published on.

        Returns:
            One transform per edge in the topic. A later edge for the same child frame
            is included as its own entry; the caller decides which one to keep. A
            message that cannot be decoded, or holds no transform, is skipped.
        """
        return list(self._cached_static_transforms(topic=topic))

    def get_decoded_message_at(
        self,
        channel_id: int,
        timestamp_ns: int,
    ) -> DecodedMessage | None:
        """Returns the decoded message at an exact timestamp on a channel.

        Unlike `get_frame_locators`, does not require pre-loading the topic with
        `load_data_for_topics`. Use this for on-demand single-frame access, e.g.
        serving one frame over HTTP without loading the full recording into memory.

        Only reads the chunks whose time range contains `timestamp_ns`, so reading one
        frame does not require downloading or scanning the rest of a remote recording.

        Args:
            channel_id: The channel to read, e.g. a camera channel located through
                `get_topics`.
            timestamp_ns: The exact log time to fetch, in nanoseconds.

        Returns:
            The message at `timestamp_ns`, or `None` if no message exists at that time.

        Raises:
            ChannelNotFoundError: If the channel id is not in the file.
            McapAccessError: If the channel's messages cannot be decoded, e.g. because
                their encoding has no matching decoder factory.
        """
        topic_info = self._topic_index.require_channel_info(channel_id)
        try:
            for _, channel, message, decoded_message in self._reader.iter_decoded_messages(
                topics=[topic_info.name],
                start_time=timestamp_ns,
                end_time=timestamp_ns + 1,
            ):
                if channel.id == channel_id and message.log_time == timestamp_ns:
                    return DecodedMessage(
                        channel_id=channel_id,
                        topic=topic_info.name,
                        log_time_ns=message.log_time,
                        schema_name=topic_info.schema_name,
                        decoded_message=decoded_message,
                    )
        except (DecoderNotFoundError, UnicodeDecodeError, ValueError) as exc:
            raise McapAccessError(
                f"Cannot decode the messages of channel {channel_id} in '{self.path}': {exc}"
            ) from exc
        return None

    def iter_decoded_messages(self, topic: str) -> Iterator[tuple[int, Any]]:
        """Yields the log time and the payload of every decoded message on a topic.

        Raises:
            TopicNotFoundError: If the topic is not in the file.
            McapAccessError: If a message on the topic cannot be decoded, e.g.
                because no decoder factory is registered for its encoding.
        """
        return session.iter_decoded_messages(
            mcap_reader=self._reader, topics=self._topic_index, path=self.path, topic=topic
        )

    def get_topics(self) -> list[TopicInfo]:
        """Returns the topics of the file, ordered by name.

        A topic can be recorded on more than one channel, which gives one entry per
        channel. Reading the topics only reads the file's summary section (footer and
        summary, not the message chunks), so it does not require downloading or
        indexing the whole file: a remote file behind a filesystem that supports range
        requests (local disk, S3, GCS, or plain HTTP) is summarized cheaply.
        """
        return self._topic_index.topics()

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

    def _cached_static_transforms(self, topic: str) -> list[StaticTransform]:
        """Returns the transforms of a static topic, or none if the topic is not in the file."""
        if topic not in self._static_transforms_by_topic:
            self._static_transforms_by_topic[topic] = (
                calibration.read_transforms(
                    mcap_reader=self._reader,
                    decoder=self._decoder,
                    path=self.path,
                    topic=topic,
                )
                if self._topic_index.has_topic(topic)
                else []
            )
        return self._static_transforms_by_topic[topic]
