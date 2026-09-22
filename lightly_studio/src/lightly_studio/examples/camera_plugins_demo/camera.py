"""Background reader for an RTSP stream, a webcam, or a video file."""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray

logger = logging.getLogger(__name__)

# RTSP over TCP drops fewer frames than the default UDP transport on busy networks.
os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")

_RECONNECT_DELAY_S = 2.0
_FPS_WINDOW_S = 2.0


@dataclass(frozen=True)
class Frame:
    """One decoded camera frame.

    Attributes:
        image: BGR image of shape (H, W, 3) with dtype uint8.
        index: Increasing frame counter. It does not reset when the source changes.
        timestamp: Wall-clock time when the frame was read, in seconds since the epoch.
    """

    image: NDArray[np.uint8]
    index: int
    timestamp: float


@dataclass(frozen=True)
class CameraStatus:
    """Current state of the camera reader."""

    source: str
    connected: bool
    fps: float
    width: int
    height: int
    error: str


class CameraStream:
    """Reads frames from a camera source in a background thread.

    The source can be an RTSP or HTTP URL, a webcam index such as "0", or a path to a
    video file. Video files play at their native frame rate and loop, so a file can
    stand in for a live camera. The reader reconnects when the source drops.
    """

    def __init__(self, source: str) -> None:
        """Create a reader for a camera source without opening it yet."""
        self._source = source
        self._frame: Frame | None = None
        self._next_index = 0
        self._condition = threading.Condition()
        self._stop_event = threading.Event()
        self._source_changed = threading.Event()
        self._thread: threading.Thread | None = None
        self._connected = False
        self._error = ""
        self._frame_times: list[float] = []

    def start(self) -> None:
        """Start the reader thread."""
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="camera-reader", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the reader thread and release the source."""
        self._stop_event.set()
        with self._condition:
            self._condition.notify_all()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def set_source(self, source: str) -> None:
        """Switch to a different camera source."""
        self._source = source
        self._source_changed.set()

    def latest_frame(self) -> Frame | None:
        """Return the most recent frame, or None if no frame was read yet."""
        with self._condition:
            return self._frame

    def wait_for_frame(self, after_index: int, timeout: float) -> Frame | None:
        """Block until a frame newer than `after_index` is available.

        Args:
            after_index: Index of the last frame the caller has seen. Use -1 for any frame.
            timeout: Maximum wait time in seconds.

        Returns:
            The newest frame, or None if no newer frame arrived before the timeout.
        """
        deadline = time.monotonic() + timeout
        with self._condition:
            while self._frame is None or self._frame.index <= after_index:
                remaining = deadline - time.monotonic()
                if remaining <= 0 or self._stop_event.is_set():
                    return None
                self._condition.wait(timeout=remaining)
            return self._frame

    def status(self) -> CameraStatus:
        """Return a snapshot of the reader state."""
        frame = self.latest_frame()
        now = time.monotonic()
        recent = [t for t in self._frame_times if now - t <= _FPS_WINDOW_S]
        fps = len(recent) / _FPS_WINDOW_S if recent else 0.0
        return CameraStatus(
            source=self._source,
            connected=self._connected,
            fps=round(fps, 1),
            width=frame.image.shape[1] if frame is not None else 0,
            height=frame.image.shape[0] if frame is not None else 0,
            error=self._error,
        )

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self._source_changed.clear()
            source = self._source
            capture = _open_capture(source=source)
            if capture is None or not capture.isOpened():
                self._set_disconnected(error=f"Cannot open camera source '{source}'.")
                self._source_changed.wait(timeout=_RECONNECT_DELAY_S)
                continue

            is_file = _is_video_file(source=source)
            file_fps = capture.get(cv2.CAP_PROP_FPS) if is_file else 0.0
            frame_interval = 1.0 / file_fps if file_fps and file_fps > 0 else 0.0
            logger.info("Camera connected: %s", source)
            self._connected = True
            self._error = ""
            next_frame_time = time.monotonic()

            while not self._stop_event.is_set() and not self._source_changed.is_set():
                ok, image = capture.read()
                if not ok:
                    if is_file:
                        # Loop the video file so it behaves like a live feed.
                        capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    self._set_disconnected(error=f"Lost connection to '{source}'. Reconnecting.")
                    break
                if frame_interval:
                    next_frame_time += frame_interval
                    sleep_s = next_frame_time - time.monotonic()
                    if sleep_s > 0:
                        time.sleep(sleep_s)
                    else:
                        next_frame_time = time.monotonic()
                self._publish(image=image)

            capture.release()
            if not self._source_changed.is_set() and not self._stop_event.is_set():
                self._stop_event.wait(timeout=_RECONNECT_DELAY_S)

    def _publish(self, image: NDArray[np.uint8]) -> None:
        now = time.monotonic()
        self._frame_times = [t for t in self._frame_times if now - t <= _FPS_WINDOW_S]
        self._frame_times.append(now)
        with self._condition:
            self._frame = Frame(image=image, index=self._next_index, timestamp=time.time())
            self._next_index += 1
            self._condition.notify_all()

    def _set_disconnected(self, error: str) -> None:
        if error != self._error:
            logger.warning(error)
        self._connected = False
        self._error = error


def encode_jpeg(image: NDArray[np.uint8], quality: int = 80) -> bytes:
    """Encode a BGR image as JPEG bytes."""
    ok, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise ValueError("Failed to encode frame as JPEG.")
    return bytes(buffer.tobytes())


def _open_capture(source: str) -> cv2.VideoCapture | None:
    try:
        if source.isdigit():
            return cv2.VideoCapture(int(source))
        return cv2.VideoCapture(source, cv2.CAP_FFMPEG)
    except cv2.error:
        logger.exception("OpenCV failed to open '%s'.", source)
        return None


def _is_video_file(source: str) -> bool:
    return not source.isdigit() and "://" not in source and Path(source).is_file()
