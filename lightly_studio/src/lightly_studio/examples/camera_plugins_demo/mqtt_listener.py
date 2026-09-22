"""Print the MQTT messages the demo publishes.

This stands for the other software or hardware that listens to the camera:

    python -m lightly_studio.examples.camera_plugins_demo.mqtt_listener --host localhost
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from typing import Any

from paho.mqtt import client as mqtt_client  # type: ignore[import-untyped]


def main() -> None:
    """Subscribe to the demo topics and print every message."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--topic", default="lightly/camera/#")
    args = parser.parse_args()

    client = mqtt_client.Client(callback_api_version=mqtt_client.CallbackAPIVersion.VERSION2)
    client.on_connect = lambda c, _userdata, _flags, _reason, _properties: c.subscribe(args.topic)
    client.on_message = _print_message
    client.connect(args.host, args.port)
    print(f"Listening on {args.host}:{args.port}, topic {args.topic}. Ctrl+C to stop.")
    client.loop_forever()


def _print_message(_client: Any, _userdata: Any, message: Any) -> None:
    payload = json.loads(message.payload)
    stamp = datetime.fromtimestamp(payload["timestamp"], tz=timezone.utc).astimezone()
    stamp_text = stamp.strftime("%H:%M:%S")
    if payload["type"] == "count_changed":
        body = f"{payload['class']}: {payload['previous']} -> {payload['current']}"
    else:
        counts = ", ".join(f"{name} x{count}" for name, count in payload["counts"].items())
        body = counts or "nothing in view"
    print(f"{stamp_text}  {message.topic:32s}  {body}")


if __name__ == "__main__":
    main()
