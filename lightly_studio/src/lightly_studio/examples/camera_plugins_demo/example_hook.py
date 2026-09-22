"""Example custom script that reacts to detections from the deployed model.

Point the demo at this file to run it:

    python -m lightly_studio.examples.camera_plugins_demo.run_camera_demo \
        --hook-script src/lightly_studio/examples/camera_plugins_demo/example_hook.py

This stands for the customer-side integration: a PLC write, a GPIO pin, an HTTP call to
a line controller. Both functions are optional. A returned string shows up in the event
log of the Camera Station page.

Signals in this example:

- `on_event` fires when the number of objects of a class changes.
- `on_detections` fires at most once per second with every current detection.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

ALERT_CLASS = "person"
ALERT_SCORE = 0.7
LOG_FILE = Path("camera_demo_data/detections.csv")
BUSY_SCENE_OBJECTS = 3


def on_event(message: dict[str, Any]) -> str | None:
    """React to a class count that changed."""
    if message["class"] == ALERT_CLASS and message["current"] > message["previous"]:
        _write_row(message=message)
        return f"ALERT: {ALERT_CLASS} in view -> stop signal sent"
    return None


def on_detections(message: dict[str, Any]) -> str | None:
    """React to the current detections."""
    strong = [d for d in message["detections"] if d["score"] >= ALERT_SCORE]
    if not strong:
        return None
    return None if len(strong) < BUSY_SCENE_OBJECTS else f"{len(strong)} objects in view"


def _write_row(message: dict[str, Any]) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    is_new = not LOG_FILE.exists()
    with LOG_FILE.open("a", newline="") as file:
        writer = csv.writer(file)
        if is_new:
            writer.writerow(["timestamp", "model", "class", "count"])
        writer.writerow(
            [message["timestamp"], message["model"], message["class"], message["current"]]
        )
