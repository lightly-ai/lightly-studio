"""Decoding displayable frames from compressed video messages.

Handles `foxglove_msgs/msg/CompressedVideo` (and the equivalent Foxglove schema),
which carry Annex B H.264 or H.265 bitstreams. A single message may be a keyframe or
a delta frame. A delta frame can only be decoded after the frames it depends on, so
`VideoDecoder` is fed every message from the preceding keyframe up to the target
frame, e.g. as read by `McapFileReader.get_decoded_messages_in_range`.

The frame is decoded with PyAV (libav) and re-encoded as JPEG so the result is
directly servable from an HTTP endpoint without any further processing.
"""

from __future__ import annotations

import io
from typing import Any

import av
from av import CodecContext, VideoFrame
from av.codec.context import ThreadType
from PIL import Image

from lightly_studio.core.mcap import _video_formats, message_fields
from lightly_studio.core.mcap.errors import McapAccessError

JPEG_QUALITY = 85


class VideoDecoder:
    """Decodes the messages of one video channel in order, starting at a keyframe.

    The codec uses slice threading with one thread, so each picture is emitted as
    its access unit is fed. The decoder keeps that state. A later call continues
    with the next message instead of decoding from the keyframe again.

    Attributes:
        keyframe_log_time_ns: The log time of the keyframe the decoder starts at.
        last_log_time_ns: The log time of the last message fed to the decoder, or
            `None` before the first message.
    """

    def __init__(self, keyframe_log_time_ns: int) -> None:
        """Creates a decoder that starts at a keyframe.

        Args:
            keyframe_log_time_ns: The log time of the keyframe. The first message fed
                to `decode` must be this keyframe.
        """
        self.keyframe_log_time_ns = keyframe_log_time_ns
        self.last_log_time_ns: int | None = None
        self._codec: CodecContext | None = None
        self._codec_name = ""
        self._frames: dict[int, VideoFrame] = {}
        self._is_flushed = False

    def can_continue_to(self, keyframe_log_time_ns: int, log_time_ns: int) -> bool:
        """Returns whether the decoder can produce the frame at `log_time_ns`.

        The decoder can produce it if it started at the same keyframe and either
        already holds that picture, or it has not passed `log_time_ns` and was not
        flushed.

        Args:
            keyframe_log_time_ns: The log time of the keyframe of the target frame.
            log_time_ns: The log time of the target frame.
        """
        if self.keyframe_log_time_ns != keyframe_log_time_ns:
            return False
        if self.has_frame(log_time_ns):
            return True
        return (
            not self._is_flushed
            and self.last_log_time_ns is not None
            and self.last_log_time_ns < log_time_ns
        )

    def has_frame(self, log_time_ns: int) -> bool:
        """Returns whether the picture at `log_time_ns` has already been emitted."""
        return log_time_ns in self._frames

    def frame(self, log_time_ns: int) -> VideoFrame | None:
        """Returns the picture at `log_time_ns`, or `None` if it was not emitted."""
        return self._frames.get(log_time_ns)

    def is_reusable(self) -> bool:
        """Returns whether a later request can use this decoder.

        A flushed decoder is reusable only for pictures it already holds. A decoder
        that has not been fed is not worth caching.
        """
        if self._is_flushed:
            return bool(self._frames)
        return self.last_log_time_ns is not None

    def decode(
        self, decoded_message: Any, log_time_ns: int, retain_log_time_ns: int | None = None
    ) -> None:
        """Feeds the next message of the channel to the decoder.

        Pictures emitted with a log time before `retain_log_time_ns` are discarded.
        The target picture and any picture after it are kept, so a catch-up to the
        target does not copy the frames in between.

        Args:
            decoded_message: A decoded compressed video message with `data` (bytes,
                Annex B) and `format` (str, e.g. ``"h265"``) fields.
            log_time_ns: The log time of the message. Must be later than the log
                time of the last message.
            retain_log_time_ns: The earliest picture log time to keep. Defaults to
                `log_time_ns`, so earlier emitted pictures are discarded.

        Raises:
            ValueError: If the decoder was flushed, or `log_time_ns` is not later
                than the log time of the last message.
            McapAccessError: If the message fields are missing, the video format is
                not supported (not H.264 or H.265), or PyAV cannot decode the payload.
                The decoder cannot decode further after PyAV fails.
        """
        if self._is_flushed:
            raise ValueError("Cannot decode with a flushed decoder.")
        if self.last_log_time_ns is not None and log_time_ns <= self.last_log_time_ns:
            raise ValueError(
                f"Log time {log_time_ns} must be later than the log time of the last "
                f"message {self.last_log_time_ns}."
            )
        data, video_format = _payload(decoded_message=decoded_message)
        if self._codec is None:
            self._codec_name = _codec_name(video_format=video_format)
            self._codec = _open_decoder(codec_name=self._codec_name)
        retain_from_ns = log_time_ns if retain_log_time_ns is None else retain_log_time_ns
        # Each MCAP message is one complete Annex B access unit, so wrap it directly
        # as a packet rather than using codec.parse(), which buffers across calls and
        # returns nothing for a single isolated payload. The packet time identifies
        # the picture of each message.
        packet = av.Packet(data)
        packet.pts = log_time_ns
        try:
            frames = self._codec.decode(packet)  # type: ignore[attr-defined]
        except av.FFmpegError as exc:
            # The codec state is unknown after a failure, so later messages must not use it.
            self._is_flushed = True
            raise McapAccessError(
                f"PyAV could not decode the {self._codec_name} payload: {exc}"
            ) from exc
        self.last_log_time_ns = log_time_ns
        _retain_frames(frames=frames, retained=self._frames, retain_from_ns=retain_from_ns)

    def require_frame(self, log_time_ns: int) -> VideoFrame:
        """Returns the picture at `log_time_ns`.

        Raises:
            McapAccessError: If that picture was not emitted.
        """
        frame = self.frame(log_time_ns)
        if frame is None:
            raise McapAccessError(f"No decodable frame found in the {self._codec_name} payload.")
        return frame

    def release_frames_up_to(self, log_time_ns: int) -> None:
        """Drops pictures at or before `log_time_ns`. Later pictures stay available."""
        stale = [pts for pts in self._frames if pts <= log_time_ns]
        for pts in stale:
            del self._frames[pts]

    def flush(self, retain_log_time_ns: int = 0) -> None:
        """Emits pictures the decoder still holds. The decoder cannot decode further.

        A slice-threaded decoder emits each picture from `decode`. This is the
        fallback for a picture that was not emitted with its access unit.

        Args:
            retain_log_time_ns: The earliest picture log time to keep.

        Raises:
            McapAccessError: If PyAV cannot decode the buffered pictures.
        """
        if self._is_flushed or self._codec is None:
            self._is_flushed = True
            return
        self._is_flushed = True
        try:
            frames = self._codec.decode(None)  # type: ignore[attr-defined]
        except av.FFmpegError as exc:
            raise McapAccessError(
                f"PyAV could not decode the {self._codec_name} payload: {exc}"
            ) from exc
        _retain_frames(frames=frames, retained=self._frames, retain_from_ns=retain_log_time_ns)


def from_decoded_message(
    decoded_message: Any,
    width: int | None = None,
    height: int | None = None,
    quality: int = JPEG_QUALITY,
) -> bytes:
    """Decodes the frame of a single compressed video message as JPEG.

    Only keyframes are fully decodable in isolation. A delta frame without its
    preceding frames either produces a corrupted image or raises an error. Use
    `VideoDecoder` to decode a delta frame.

    Args:
        decoded_message: A decoded compressed video message with `data` (bytes,
            Annex B) and `format` (str, e.g. ``"h265"``) fields.
        width: If set, resize the output to this width in pixels. Aspect ratio is
            preserved when only one of `width` / `height` is given.
        height: If set, resize the output to this height in pixels. Aspect ratio is
            preserved when only one of `width` / `height` is given.
        quality: JPEG quality (1-95). Defaults to `JPEG_QUALITY`.

    Returns:
        JPEG-encoded bytes of the decoded frame.

    Raises:
        McapAccessError: If the message fields are missing, the video format is not
            supported (not H.264 or H.265), or PyAV cannot decode the payload.
    """
    decoder = VideoDecoder(keyframe_log_time_ns=0)
    decoder.decode(decoded_message=decoded_message, log_time_ns=0)
    frame = decoder.frame(log_time_ns=0)
    if frame is None:
        decoder.flush()
        frame = decoder.require_frame(log_time_ns=0)
    return to_jpeg(frame=frame, width=width, height=height, quality=quality)


def to_jpeg(
    frame: VideoFrame,
    width: int | None = None,
    height: int | None = None,
    quality: int = JPEG_QUALITY,
) -> bytes:
    """Encodes a decoded video frame as JPEG.

    Args:
        frame: The decoded frame, e.g. from `VideoDecoder.frame`.
        width: If set, resize the output to this width in pixels. Aspect ratio is
            preserved when only one of `width` / `height` is given.
        height: If set, resize the output to this height in pixels. Aspect ratio is
            preserved when only one of `width` / `height` is given.
        quality: JPEG quality (1-95). Defaults to `JPEG_QUALITY`.

    Returns:
        JPEG-encoded bytes of the frame.
    """
    image = Image.fromarray(frame.to_ndarray(format="rgb24"))
    if width is not None or height is not None:
        image = _resize(image, width=width, height=height)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality, subsampling=2)
    return buffer.getvalue()


def _open_decoder(codec_name: str) -> CodecContext:
    """Opens a decoder that emits each picture as its access unit is fed.

    Frame threading delays output by several access units, which forces a flush
    to see the picture and drops the reference frames. Slice threading with one
    thread emits each picture as its access unit is fed.
    """
    codec = av.CodecContext.create(codec_name, "r")
    codec.thread_type = ThreadType.SLICE
    codec.thread_count = 1
    return codec


def _retain_frames(
    frames: list[VideoFrame], retained: dict[int, VideoFrame], retain_from_ns: int
) -> None:
    """Copies pictures at or after `retain_from_ns` out of the decoder buffers.

    The next packet reuses those buffers, so a picture that is kept must be copied
    before `decode` is called again.
    """
    for frame in frames:
        if frame.pts is None or frame.pts < retain_from_ns:
            continue
        retained[int(frame.pts)] = frame.reformat(format=frame.format.name)


def _payload(decoded_message: Any) -> tuple[bytes, str]:
    """Returns the Annex B data and the format string of a compressed video message.

    Raises:
        McapAccessError: If a field is missing or has the wrong type.
    """
    data = message_fields.require_field(decoded_message, _video_formats.DATA_FIELDS)
    video_format = message_fields.require_field(decoded_message, _video_formats.FORMAT_FIELDS)
    if not isinstance(data, (bytes, bytearray)):
        raise McapAccessError(
            f"Compressed video message has a non-byte 'data' field: {type(data).__name__}."
        )
    if not isinstance(video_format, str):
        raise McapAccessError(
            f"Compressed video message has a non-string 'format' field: "
            f"{type(video_format).__name__}."
        )
    return bytes(data), video_format


def _codec_name(video_format: str) -> str:
    """Returns the libav codec name for a recorded format string.

    Raises:
        McapAccessError: If the format is not H.264 or H.265.
    """
    normalized = _video_formats.normalize_format(video_format)
    if normalized in _video_formats.H264_FORMATS:
        return "h264"
    if normalized in _video_formats.H265_FORMATS:
        return "hevc"
    raise McapAccessError(
        f"Unsupported compressed video format: '{video_format}'. "
        f"Only H.264 and H.265 are supported."
    )


def _resize(image: Image.Image, width: int | None, height: int | None) -> Image.Image:
    """Resizes an image, preserving aspect ratio when only one dimension is given."""
    orig_w, orig_h = image.size
    if width is None:
        assert height is not None
        width = max(1, round(orig_w * height / orig_h))
    elif height is None:
        height = max(1, round(orig_h * width / orig_w))
    return image.resize((width, height), Image.Resampling.LANCZOS)
