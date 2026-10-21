"""Build the Wayve demo datasets from the 50 Nexar clips picked by `pick_clips.py`.

The Postgres database in `config.DB_URL` holds two datasets:

- `nexar-frames`: one JPEG image per clip second, with YOLO boxes, frame metadata and
  embeddings. The few-shot classifier and the GUI query editor work on image datasets only.
- `nexar-clips`: the videos, with one embedding per clip and the Nexar labels as metadata.
  Video frames have no embeddings.

The script creates `nexar-clips` last, because the GUI root opens the newest dataset.
It deletes all data in the database first.

Run from `lightly_studio/` with the venv from the README:

    python src/lightly_studio/examples/wayve_demo/build_dataset.py
"""

from __future__ import annotations

import csv
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
from lightly_studio.examples.wayve_demo import config

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
    """Extract and detect the frames, then index the frames and the clips."""
    clips = {
        row["file_name"]: row for row in csv.DictReader((config.NEXAR_DIR / "selection.csv").open())
    }
    config.connect(cleanup_existing=True)

    model = YOLO(str(config.YOLO_WEIGHTS))
    config.FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    boxes_by_image: dict[str, list[Box]] = {}
    for file_name in sorted(clips):
        images = _extract_seconds(video_path=config.VIDEOS_DIR / file_name)
        print(f"Detecting objects in {file_name} ({len(images)} frames)")
        for second, image in enumerate(images):
            image_name = f"{Path(file_name).stem}_{second:02d}.jpg"
            cv2.imwrite(str(config.FRAMES_DIR / image_name), image)
            boxes_by_image[image_name] = _detect(model=model, image=image)

    frames = ls.ImageDataset.create(name=config.FRAMES_DATASET)
    frames.add_images_from_path(path=config.FRAMES_DIR, embed=True)
    for frame in frames:
        clip_stem, second_str = Path(frame.file_name).stem.rsplit("_", maxsplit=1)
        clip = clips[f"{clip_stem}.mp4"]
        _set_clip_metadata(sample=frame, clip=clip)
        _set_frame_labels(
            sample=frame,
            boxes=boxes_by_image[frame.file_name],
            clip=clip,
            timestamp_s=float(second_str),
        )

    videos = ls.VideoDataset.create(name=config.CLIPS_DATASET)
    videos.add_videos_from_path(
        path=config.VIDEOS_DIR, embed=True, embed_frames=False, target_fps=1
    )
    for video in videos:
        _set_clip_metadata(sample=video, clip=clips[video.file_name])
    print(f"Done: {len(boxes_by_image)} frames, {len(clips)} clips")


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


def _extract_seconds(video_path: Path) -> list[NDArray[np.uint8]]:
    """Decode the video once and keep the frame at each whole second, from second 0.

    The frame for second `s` has index `round(s * fps)`.
    """
    capture = cv2.VideoCapture(str(video_path))
    fps = capture.get(cv2.CAP_PROP_FPS)
    images: list[NDArray[np.uint8]] = []
    index = 0
    while True:
        ok, image = capture.read()
        if not ok:
            break
        if index == round(len(images) * fps):
            images.append(image)
        index += 1
    capture.release()
    if not images:
        raise RuntimeError(f"{video_path.name}: could not decode any frame")
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
