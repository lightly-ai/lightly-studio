"""Version 1 of "their filter": tag clips that look like near-misses.

The filter reads only what a customer pipeline would have: the clip conditions and the
per-frame YOLO counts. The Nexar `near_miss` label is the ground truth, and the script
prints where the filter is wrong, so the demo can show those clips in the GUI.

Run from `lightly_studio/` with the venv from the README. Refresh the GUI after it:

    python src/lightly_studio/examples/wayve_demo/filter_v1.py
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import lightly_studio as ls
from lightly_studio.examples.wayve_demo import clear_tag, config

TAG = "filter_v1"
MIN_VEHICLE_AREA = 0.13
FRAME_KEYS = ("timestamp_s", "n_persons", "n_vehicles", "max_vehicle_area", "max_person_conf")


def main() -> None:
    """Tag the clips the filter selects and print its errors."""
    config.connect()
    frames_by_clip: dict[str, list[dict[str, Any]]] = {}
    for frame in ls.ImageDataset.load(name=config.FRAMES_DATASET):
        frames_by_clip.setdefault(frame.metadata["clip"], []).append(
            {key: frame.metadata[key] for key in FRAME_KEYS}
        )

    videos = ls.VideoDataset.load(name=config.CLIPS_DATASET)
    clear_tag.clear_tag(samples=videos, tag=TAG)
    errors: dict[str, list[str]] = {"missed": [], "false_positive": []}
    for video in videos:
        clip = {key: video.metadata[key] for key in ("light_conditions", "weather", "scene")}
        frames = sorted(frames_by_clip[video.file_name], key=lambda f: f["timestamp_s"])
        selected = looks_like_near_miss(clip=clip, frames=frames)
        if selected:
            video.add_tag(name=TAG)
        is_near_miss = video.metadata["near_miss"]
        if is_near_miss and not selected:
            errors["missed"].append(video.file_name)
        elif selected and not is_near_miss:
            errors["false_positive"].append(video.file_name)

    for kind, names in errors.items():
        print(f"{kind} ({len(names)}): {', '.join(sorted(names))}")


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


if __name__ == "__main__":
    main()
