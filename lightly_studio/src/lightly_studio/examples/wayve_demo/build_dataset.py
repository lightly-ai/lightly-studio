"""Build the Wayve demo database from the 50 Nexar clips picked by `pick_clips.py`.

The database holds two datasets:

- `nexar-clips`: a video dataset with one embedding per clip and one per frame (1 fps).
  Clips carry the Nexar labels as metadata. Frames carry YOLO boxes and counts.
- `nexar-frames`: the same frames as JPEG images, for the few-shot classifier and the
  GUI query editor, which work on image datasets only.

Run from `lightly_studio/`:

    uv run python src/lightly_studio/examples/wayve_demo/build_dataset.py
"""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray
from ultralytics.engine.results import Results
from ultralytics.models import YOLO

import lightly_studio as ls
from lightly_studio.core.annotation.annotation_create import CreateObjectDetection
from lightly_studio.core.sample import Sample
from lightly_studio.core.video.video_frame_sample import VideoFrameSample
from lightly_studio.database import db_manager

DATA_DIR = Path.home() / "demo_data/wayve"
NEXAR_DIR = DATA_DIR / "nexar"
VIDEOS_DIR = NEXAR_DIR / "videos"
FRAMES_DIR = NEXAR_DIR / "frames"
DB_FILE = DATA_DIR / "wayve.db"
YOLO_WEIGHTS = DATA_DIR / "yolo11n.pt"

ANNOTATION_SOURCE = "yolo11n"
MIN_CONFIDENCE = 0.35
VEHICLE_CLASSES = {"car", "truck", "bus", "motorcycle"}
KEPT_CLASSES = VEHICLE_CLASSES | {"person", "bicycle"}


@dataclass
class Box:
    """One YOLO detection in pixel coordinates."""

    class_name: str
    confidence: float
    x: int
    y: int
    width: int
    height: int
    area_fraction: float
    """Box area divided by the image area."""


def main() -> None:
    """Index the videos, run YOLO on every kept frame and index the frames as images."""
    clips = {row["file_name"]: row for row in csv.DictReader((NEXAR_DIR / "selection.csv").open())}
    db_manager.connect(db_file=str(DB_FILE), cleanup_existing=True)

    videos = ls.VideoDataset.create(name="nexar-clips")
    videos.add_videos_from_path(path=VIDEOS_DIR, embed=True, embed_frames=True, target_fps=1)
    for video in videos:
        _set_clip_metadata(sample=video, clip=clips[video.file_name])

    frames_by_video: dict[str, list[VideoFrameSample]] = defaultdict(list)
    for frame in videos.frames():
        frames_by_video[frame.parent_video.file_name].append(frame)

    model = YOLO(str(YOLO_WEIGHTS))
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    boxes_by_image: dict[str, list[Box]] = {}
    times_by_image: dict[str, float] = {}
    for file_name, frames in frames_by_video.items():
        print(f"Detecting objects in {file_name} ({len(frames)} frames)")
        images = _extract_frames(
            video_path=VIDEOS_DIR / file_name,
            frame_numbers={f.frame_number for f in frames},
        )
        for frame in frames:
            image_name = f"{Path(file_name).stem}_{frame.frame_number:05d}.jpg"
            cv2.imwrite(str(FRAMES_DIR / image_name), images[frame.frame_number])
            boxes = _detect(model=model, image=images[frame.frame_number])
            boxes_by_image[image_name] = boxes
            times_by_image[image_name] = frame.frame_timestamp_s
            _set_frame_labels(
                sample=frame,
                boxes=boxes,
                clip=clips[file_name],
                timestamp_s=frame.frame_timestamp_s,
            )

    images_dataset = ls.ImageDataset.create(name="nexar-frames")
    images_dataset.add_images_from_path(path=FRAMES_DIR)
    for image in images_dataset:
        clip_name = image.file_name.rsplit("_", maxsplit=1)[0] + ".mp4"
        _set_clip_metadata(sample=image, clip=clips[clip_name])
        _set_frame_labels(
            sample=image,
            boxes=boxes_by_image[image.file_name],
            clip=clips[clip_name],
            timestamp_s=times_by_image[image.file_name],
        )
    print(f"Done: {DB_FILE}")


def _set_clip_metadata(sample: Sample, clip: dict[str, str]) -> None:
    sample.metadata.update(
        {
            "light_conditions": clip["light_conditions"],
            "weather": clip["weather"] or "Unknown",
            "scene": clip["scene"],
            "near_miss": clip["near_miss"] == "True",
            "clip": clip["file_name"],
        }
    )


def _set_frame_labels(
    sample: Sample, boxes: list[Box], clip: dict[str, str], timestamp_s: float
) -> None:
    persons = [b for b in boxes if b.class_name == "person"]
    metadata: dict[str, int | float] = {
        "n_persons": len(persons),
        "n_vehicles": sum(b.class_name in VEHICLE_CLASSES for b in boxes),
        # The nearest vehicle has the largest box, so this is a proxy for distance.
        "max_vehicle_area": max(
            (b.area_fraction for b in boxes if b.class_name in VEHICLE_CLASSES), default=0.0
        ),
        "max_person_conf": max((b.confidence for b in persons), default=0.0),
        "timestamp_s": round(timestamp_s, 2),
    }
    # Near-miss clips have the event time. A negative value means the frame is after it.
    if clip["time_of_event"]:
        metadata["seconds_to_event"] = round(float(clip["time_of_event"]) - timestamp_s, 2)
    sample.metadata.update(metadata)
    if boxes:
        sample.add_annotations(
            annotations=[
                CreateObjectDetection(
                    class_name=b.class_name,
                    confidence=b.confidence,
                    x=b.x,
                    y=b.y,
                    width=b.width,
                    height=b.height,
                )
                for b in boxes
            ],
            annotation_source=ANNOTATION_SOURCE,
        )


def _extract_frames(video_path: Path, frame_numbers: set[int]) -> dict[int, NDArray[np.uint8]]:
    """Decode the video once and keep the frames with the given numbers."""
    capture = cv2.VideoCapture(str(video_path))
    images: dict[int, NDArray[np.uint8]] = {}
    index = 0
    while len(images) < len(frame_numbers):
        ok, image = capture.read()
        if not ok:
            break
        if index in frame_numbers:
            images[index] = image
        index += 1
    capture.release()
    missing = frame_numbers - images.keys()
    if missing:
        raise RuntimeError(f"{video_path.name}: could not decode frames {sorted(missing)}")
    return images


def _detect(model: YOLO, image: NDArray[np.uint8]) -> list[Box]:
    result = next(iter(model.predict(image, conf=MIN_CONFIDENCE, verbose=False)))
    assert isinstance(result, Results)
    assert result.boxes is not None
    image_area = image.shape[0] * image.shape[1]
    boxes = []
    for (x1, y1, x2, y2), cls, conf in zip(
        result.boxes.xyxy.tolist(), result.boxes.cls.tolist(), result.boxes.conf.tolist()
    ):
        class_name = result.names[int(cls)]
        if class_name not in KEPT_CLASSES:
            continue
        boxes.append(
            Box(
                class_name=class_name,
                confidence=round(conf, 3),
                x=int(x1),
                y=int(y1),
                width=int(x2 - x1),
                height=int(y2 - y1),
                area_fraction=round((x2 - x1) * (y2 - y1) / image_area, 4),
            )
        )
    return boxes


if __name__ == "__main__":
    main()
