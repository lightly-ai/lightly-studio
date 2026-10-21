"""Version 1 of "their filter": tag clips that look like near-misses, then open the GUI.

The filter reads only what a customer pipeline would have: the clip conditions and the
per-frame YOLO counts. The Nexar `near_miss` label is the ground truth, and the script
prints where the filter is wrong, so the demo can show those clips in the GUI.

Run from `lightly_studio/` after `build_dataset.py`:

    uv run python src/lightly_studio/examples/wayve_demo/filter_v1.py
"""

from __future__ import annotations

import threading
import time
import urllib.error
import urllib.request
import webbrowser
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import lightly_studio as ls
from lightly_studio.database import db_manager

DB_FILE = Path.home() / "demo_data/wayve/wayve.db"
TAG = "filter_v1"
MIN_VEHICLE_AREA = 0.13
FRAME_KEYS = ("timestamp_s", "n_persons", "n_vehicles", "max_vehicle_area", "max_person_conf")


def main() -> None:
    """Tag the clips the filter selects, print its errors and start the GUI."""
    db_manager.connect(db_file=str(DB_FILE), must_exist=True)
    videos = ls.VideoDataset.load(name="nexar-clips")

    frames_by_clip: dict[str, list[dict[str, Any]]] = {}
    for frame in videos.frames():
        clip_name = frame.parent_video.file_name
        frames_by_clip.setdefault(clip_name, []).append(
            {key: frame.metadata[key] for key in FRAME_KEYS}
        )

    errors: dict[str, list[str]] = {"missed": [], "false_positive": []}
    for video in videos:
        clip = {key: video.metadata[key] for key in ("light_conditions", "weather", "scene")}
        frames = sorted(frames_by_clip[video.file_name], key=lambda f: f["timestamp_s"])
        selected = looks_like_near_miss(clip=clip, frames=frames)
        if TAG in video.tags:
            video.remove_tag(TAG)
        if selected:
            video.add_tag(TAG)
        is_near_miss = video.metadata["near_miss"]
        if is_near_miss and not selected:
            errors["missed"].append(video.file_name)
        elif selected and not is_near_miss:
            errors["false_positive"].append(video.file_name)

    for kind, names in errors.items():
        print(f"{kind} ({len(names)}): {', '.join(sorted(names))}", flush=True)
    _serve_clips(videos=videos)


# `clip` is unused in version 1. The live demo edit adds a condition on it.
def looks_like_near_miss(clip: Mapping[str, str], frames: Sequence[Mapping[str, Any]]) -> bool:  # noqa: ARG001
    """Decide if a clip is a near-miss candidate.

    Args:
        clip: Clip conditions: `light_conditions` (Normal, Dark, Twilight, Bright),
            `weather` and `scene`.
        frames: One entry per frame at 1 fps, sorted by `timestamp_s`. Each has
            `n_persons`, `n_vehicles`, `max_person_conf` and `max_vehicle_area` from
            YOLO. `max_vehicle_area` is the largest vehicle box divided by the frame
            area, so it rises as a vehicle comes close.

    Returns:
        True if the clip goes into the `filter_v1` tag.
    """
    # A vehicle close enough to fill this much of the frame is a near-miss candidate.
    return bool(max(f["max_vehicle_area"] for f in frames) >= MIN_VEHICLE_AREA)


def _serve_clips(videos: ls.VideoDataset) -> None:
    """Start the GUI and open it on the clips.

    The GUI root opens the newest dataset, which is `nexar-frames`. So the script opens
    the clips URL itself.
    """
    server = ls.start_gui_background()
    url = f"{server.url}/datasets/{videos.collection_id}/video/{videos.collection_id}"
    print(f"Clips: {url}", flush=True)
    _wait_for_server(url=server.url)
    webbrowser.open(url)
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        ls.stop_gui_background()


def _wait_for_server(url: str, timeout_s: float = 30.0) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return
        except (urllib.error.URLError, ConnectionError):
            time.sleep(0.2)
    raise TimeoutError(f"GUI did not start at {url}")


if __name__ == "__main__":
    main()
