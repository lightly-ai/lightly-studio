"""Send detection signals to other software over MQTT or a custom Python script."""

from __future__ import annotations

import collections
import importlib.util
import json
import logging
import queue
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any

from paho.mqtt import client as mqtt_client  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

_EVENT_LOG_SIZE = 50
_QUEUE_SIZE = 100


@dataclass(frozen=True)
class Detection:
    """One object detected in a camera frame.

    Attributes:
        class_name: Name of the annotation class.
        score: Confidence score in [0, 1].
        box: Bounding box as [x1, y1, x2, y2] in pixels.
    """

    class_name: str
    score: float
    box: tuple[int, int, int, int]


@dataclass(frozen=True)
class LogEntry:
    """One line in the event log that the Camera Station page shows."""

    timestamp: float
    channel: str
    message: str


@dataclass(frozen=True)
class IntegrationSettings:
    """Where detections are sent.

    Attributes:
        camera_name: Name of the camera, included in every message.
        mqtt_host: Broker host. None turns MQTT off.
        mqtt_port: Broker port.
        mqtt_topic: Topic prefix. Messages go to `<prefix>/detections` and `<prefix>/events`.
        hook_script: Python file with `on_detections` and `on_event` functions.
        interval_s: Shortest time between two "detections" messages.
        stability_s: How long a new object count has to hold before it counts as a change.
    """

    camera_name: str
    mqtt_host: str | None = None
    mqtt_port: int = 1883
    mqtt_topic: str = "lightly/camera"
    hook_script: Path | None = None
    interval_s: float = 1.0
    stability_s: float = 1.0


@dataclass
class IntegrationStatus:
    """Configuration and health of the integrations."""

    mqtt_enabled: bool
    mqtt_connected: bool
    mqtt_broker: str
    mqtt_topic: str
    hook_script: str
    hook_error: str
    events: list[LogEntry] = field(default_factory=list)


class DetectionDispatcher:
    """Forwards detections from the live model to MQTT and to a custom Python script.

    Every inference result goes in through `submit()`. Two kinds of messages go out:

    - A "detections" message with all current detections, at most once per `interval_s`
      and each time the object count of a class changes.
    - A "count_changed" event each time the count of one class changes and holds for
      `stability_s`, for example when a shoe enters or leaves the frame.

    Publishing runs in a separate thread, so a slow broker or a slow script never
    blocks inference.
    """

    def __init__(self, settings: IntegrationSettings) -> None:
        """Create the dispatcher without connecting to the broker yet."""
        self._camera_name = settings.camera_name
        self._interval_s = settings.interval_s
        self._topic = settings.mqtt_topic.rstrip("/")
        self._queue: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=_QUEUE_SIZE)
        self._events: collections.deque[LogEntry] = collections.deque(maxlen=_EVENT_LOG_SIZE)
        self._stability_s = settings.stability_s
        self._last_counts: dict[str, int] = {}
        self._pending_counts: dict[str, int] | None = None
        self._pending_since = 0.0
        self._last_publish = 0.0
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._mqtt = (
            _MqttPublisher(host=settings.mqtt_host, port=settings.mqtt_port)
            if settings.mqtt_host
            else None
        )
        self._hook = _ScriptHook(path=settings.hook_script) if settings.hook_script else None

    def start(self) -> None:
        """Connect to the broker, load the script, and start the publisher thread."""
        if self._mqtt is not None:
            self._mqtt.connect()
        if self._hook is not None:
            self._hook.load()
            if self._hook.error:
                self.log(channel="script", message=self._hook.error)
        self._thread = threading.Thread(target=self._run, name="detection-dispatcher", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the publisher thread and disconnect from the broker."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        if self._mqtt is not None:
            self._mqtt.disconnect()

    def submit(self, model_name: str, frame_index: int, detections: Sequence[Detection]) -> None:
        """Take one inference result from the live model.

        Args:
            model_name: Name of the deployed model.
            frame_index: Index of the camera frame the model processed.
            detections: Detections above the score threshold.
        """
        counts = dict(collections.Counter(d.class_name for d in detections))
        now = time.time()
        counts_changed = self._confirm_counts(counts=counts, now=now)
        for class_name in sorted(set(counts) | set(self._last_counts)) if counts_changed else []:
            previous = self._last_counts.get(class_name, 0)
            current = counts.get(class_name, 0)
            if previous != current:
                self._enqueue(
                    {
                        "type": "count_changed",
                        "timestamp": now,
                        "camera": self._camera_name,
                        "model": model_name,
                        "class": class_name,
                        "previous": previous,
                        "current": current,
                    }
                )
        if counts_changed:
            self._last_counts = counts

        if counts_changed or now - self._last_publish >= self._interval_s:
            self._last_publish = now
            self._enqueue(
                {
                    "type": "detections",
                    "timestamp": now,
                    "camera": self._camera_name,
                    "model": model_name,
                    "frame": frame_index,
                    "counts": counts,
                    "detections": [
                        {"class": d.class_name, "score": round(d.score, 3), "box": list(d.box)}
                        for d in detections
                    ],
                }
            )

    def reset(self) -> None:
        """Forget the last object counts, for example after the model changes."""
        self._last_counts = {}
        self._pending_counts = None

    def log(self, channel: str, message: str) -> None:
        """Add a line to the event log."""
        self._events.appendleft(LogEntry(timestamp=time.time(), channel=channel, message=message))

    def status(self) -> IntegrationStatus:
        """Return a snapshot of the integration state for the UI."""
        return IntegrationStatus(
            mqtt_enabled=self._mqtt is not None,
            mqtt_connected=self._mqtt.connected if self._mqtt is not None else False,
            mqtt_broker=self._mqtt.address if self._mqtt is not None else "",
            mqtt_topic=self._topic,
            hook_script=str(self._hook.path) if self._hook is not None else "",
            hook_error=self._hook.error if self._hook is not None else "",
            events=list(self._events),
        )

    def _confirm_counts(self, counts: dict[str, int], now: float) -> bool:
        """Report whether the object counts changed for long enough to signal it.

        A detector flickers: a box drops out for one frame and comes back. Without this
        check every flicker would send an event. A new count has to hold for
        `stability_s` before it counts as a change.
        """
        if counts == self._last_counts:
            self._pending_counts = None
            return False
        if counts != self._pending_counts:
            self._pending_counts = counts
            self._pending_since = now
            return False
        if now - self._pending_since < self._stability_s:
            return False
        self._pending_counts = None
        return True

    def _enqueue(self, message: dict[str, Any]) -> None:
        try:
            self._queue.put_nowait(message)
        except queue.Full:
            logger.warning("Integration queue is full. Dropping a %s message.", message["type"])

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                message = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            self._dispatch(message=message)

    def _dispatch(self, message: dict[str, Any]) -> None:
        is_event = message["type"] == "count_changed"
        if is_event:
            self.log(
                channel="event",
                message=f"{message['class']}: {message['previous']} -> {message['current']}",
            )
        if self._mqtt is not None:
            topic = f"{self._topic}/{'events' if is_event else 'detections'}"
            if self._mqtt.publish(topic=topic, payload=message) and is_event:
                self.log(channel="mqtt", message=f"Published to {topic}")
        if self._hook is not None:
            reply = self._hook.call(
                function_name="on_event" if is_event else "on_detections", payload=message
            )
            if reply:
                self.log(channel="script", message=reply)


class _MqttPublisher:
    """Publishes JSON messages to an MQTT broker and reconnects in the background."""

    def __init__(self, host: str, port: int) -> None:
        """Store the broker address without connecting."""
        self._host = host
        self._port = port
        self._client: Any = None

    @property
    def address(self) -> str:
        return f"{self._host}:{self._port}"

    @property
    def connected(self) -> bool:
        return bool(self._client is not None and self._client.is_connected())

    def connect(self) -> None:
        """Start connecting to the broker in the background."""
        self._client = mqtt_client.Client(
            callback_api_version=mqtt_client.CallbackAPIVersion.VERSION2,
            client_id="lightly-camera-station",
        )
        self._client.reconnect_delay_set(min_delay=1, max_delay=10)
        # Connect in the background so a missing broker does not stop the demo.
        self._client.connect_async(self._host, self._port)
        self._client.loop_start()

    def disconnect(self) -> None:
        """Stop the network loop and disconnect."""
        if self._client is not None:
            self._client.loop_stop()
            self._client.disconnect()

    def publish(self, topic: str, payload: Mapping[str, Any]) -> bool:
        """Publish a JSON message. Returns False when the broker is unreachable."""
        if not self.connected:
            return False
        self._client.publish(topic, json.dumps(payload), qos=0)
        return True


class _ScriptHook:
    """Calls functions in a user-provided Python file.

    The file can define `on_detections(message)` and `on_event(message)`. Both are
    optional. If a function returns a string, the string shows in the event log.
    """

    def __init__(self, path: Path) -> None:
        """Store the script path without importing it."""
        self.path = path
        self.error = ""
        self._module: ModuleType | None = None

    def load(self) -> None:
        """Import the script and remember any import error."""
        try:
            spec = importlib.util.spec_from_file_location("camera_station_hooks", self.path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Cannot import '{self.path}'.")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        except Exception as exc:
            self.error = f"Failed to load {self.path.name}: {exc}"
            logger.exception("Failed to load hook script '%s'.", self.path)
            return
        self._module = module
        logger.info("Loaded hook script %s", self.path)

    def call(self, function_name: str, payload: dict[str, Any]) -> str:
        """Call one function of the script and return what it printed back."""
        if self._module is None:
            return ""
        function: Callable[[dict[str, Any]], Any] | None = getattr(
            self._module, function_name, None
        )
        if function is None:
            return ""
        try:
            reply = function(payload)
        except Exception as exc:
            logger.exception("Hook %s failed.", function_name)
            return f"{function_name} failed: {exc}"
        return str(reply) if reply else ""
