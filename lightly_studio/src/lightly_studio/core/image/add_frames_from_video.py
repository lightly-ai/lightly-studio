"""Extract frames from a video to image files on disk.

Used by ``ImageDataset.add_frames_from_videos`` to support image-frame workflows where the
frames originate from videos. Frames are decoded with PyAV, optionally sub-sampled to a
target frame rate, and written as JPEG files so they can be treated as a normal image dataset.
"""

from __future__ import annotations

import logging
from pathlib import Path

import fsspec
from av import container

from lightly_studio.core.video.add_videos import (
    VIDEO_EXTENSIONS,
    _configure_stream_threading,
    _get_frame_rotation_deg,
)

__all__ = ["VIDEO_EXTENSIONS", "extract_frames_to_dir"]

logger = logging.getLogger(__name__)

DEFAULT_VIDEO_CHANNEL = 0
# JPEG quality for the extracted frames.
JPEG_QUALITY = 95
# Guards against dropping a frame that sits exactly on the capture boundary due to
# floating point rounding of the decoded timestamp.
_TIMESTAMP_EPSILON_S = 1e-9


def extract_frames_to_dir(
    video_path: str,
    extract_dir: Path,
    fps: float | None = None,
    video_channel: int = DEFAULT_VIDEO_CHANNEL,
    num_decode_threads: int | None = None,
) -> list[str]:
    """Decode a video and write (sub-sampled) frames as JPEG images to a directory.

    Args:
        video_path: Local or remote (e.g. ``s3://``) path to the video. Opened via fsspec,
            so the same cloud protocols as the rest of the SDK are supported.
        extract_dir: Local directory the frames are written to. Created if it does not exist.
        fps: Target frames per second. If ``None`` or ``<= 0``, every decoded frame is kept.
            Otherwise a frame is kept whenever at least ``1 / fps`` seconds have passed since
            the previously kept frame (timestamp based, so it also works for variable frame
            rate videos).
        video_channel: Index of the video stream to decode.
        num_decode_threads: Optional override for the number of FFmpeg decode threads. If
            omitted, the available CPU cores - 1 (max 16) are used.

    Returns:
        The list of written frame file paths, in decode order. Frames are named
        ``{video_stem}_{frame_number:06d}.jpg`` where ``frame_number`` is the decode index.

    # TODO(malte, 06/2026): Frames are materialized to local disk, which assumes disk space
    #   is available. Add a disk-free / streaming path (decode -> embed -> discard) so the
    #   workflow needs no extra storage.
    """
    extract_dir = Path(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)
    video_stem = Path(video_path).stem

    capture_interval_s = 1.0 / fps if fps and fps > 0 else None
    next_capture_time_s = 0.0
    written_paths: list[str] = []

    fs, fs_path = fsspec.core.url_to_fs(url=video_path)
    with fs.open(path=fs_path, mode="rb") as video_file:
        video_container = container.open(file=video_file)
        try:
            video_stream = video_container.streams.video[video_channel]
            _configure_stream_threading(
                video_stream=video_stream, num_decode_threads=num_decode_threads
            )
            time_base = video_stream.time_base

            for frame_number, frame in enumerate(video_container.decode(video_stream)):
                if frame.pts is not None and time_base is not None:
                    frame_timestamp_s = float(frame.pts * time_base)
                elif frame.time is not None:
                    # Fallback to frame.time when pts/time_base are unavailable.
                    frame_timestamp_s = frame.time
                else:
                    frame_timestamp_s = float(frame_number)

                if (
                    capture_interval_s is not None
                    and frame_timestamp_s < next_capture_time_s - _TIMESTAMP_EPSILON_S
                ):
                    continue
                if capture_interval_s is not None:
                    next_capture_time_s = frame_timestamp_s + capture_interval_s

                image = frame.to_image()
                rotation_deg = _get_frame_rotation_deg(frame=frame)
                if rotation_deg:
                    # PIL rotates counter-clockwise by the given angle, which matches the
                    # rotation the frame-serving code applies (see video_frames_media.py).
                    image = image.rotate(rotation_deg, expand=True)

                frame_path = extract_dir / f"{video_stem}_{frame_number:06d}.jpg"
                image.save(frame_path, quality=JPEG_QUALITY)
                written_paths.append(str(frame_path))
        finally:
            video_container.close()

    # Logged at debug level so it does not interleave with a progress bar over many videos.
    logger.debug(
        "Extracted %d frames from %s into %s.", len(written_paths), video_path, extract_dir
    )
    return written_paths
