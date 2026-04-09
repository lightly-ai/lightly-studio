#!/usr/bin/env python3
"""Generate overlay video for a selected YouTube-VIS sample.

This script reads YouTube-VIS annotations (`instances_50.json`) and renders
an overlay video for one selected video.

Usage examples:
    python3 scripts/generate_youtube_vis_overlay.py --list-videos
    python3 scripts/generate_youtube_vis_overlay.py --video-name 0a23765d15
    python3 scripts/generate_youtube_vis_overlay.py --video-id 81
    python3 scripts/generate_youtube_vis_overlay.py --video-name 0a23765d15 --alpha 0.5
    python3 scripts/generate_youtube_vis_overlay.py --video-name 0a23765d15 --render-mode mask
    python3 scripts/generate_youtube_vis_overlay.py --video-name 0a23765d15 --render-mode both

Outputs:
- base.mp4: copy of the selected source video
- overlay-mask.mp4: selected overlay output (bbox or mask depending on mode)
- overlay-segmentation-mask.mp4: additional mask output when `--render-mode both`
- overlay-source.json: metadata about generation
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np


DEFAULT_DATASET_ROOT = Path("lightly_studio/dataset_examples/youtube_vis_50_videos/train")
DEFAULT_OUTPUT_DIR = Path("lightly_studio_view/static/examples/assets/ytvos")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate overlay-mask.mp4 for a selected YouTube-VIS video."
    )
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=DEFAULT_DATASET_ROOT,
        help=f"Path with `instances_50.json` and `videos/` (default: {DEFAULT_DATASET_ROOT})",
    )
    parser.add_argument(
        "--instances-json",
        type=Path,
        default=None,
        help="Path to instances_50.json. Defaults to <dataset-root>/instances_50.json",
    )
    parser.add_argument(
        "--videos-dir",
        type=Path,
        default=None,
        help="Path to source videos dir. Defaults to <dataset-root>/videos",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--video-name",
        type=str,
        default=None,
        help="Video stem name, e.g. 0a23765d15",
    )
    parser.add_argument(
        "--video-id",
        type=int,
        default=None,
        help="Video id from instances_50.json",
    )
    parser.add_argument(
        "--base-output-name",
        type=str,
        default="base.mp4",
        help="Filename for copied base video (default: base.mp4)",
    )
    parser.add_argument(
        "--overlay-output-name",
        type=str,
        default="overlay-mask.mp4",
        help="Filename for primary overlay output (default: overlay-mask.mp4)",
    )
    parser.add_argument(
        "--mask-output-name",
        type=str,
        default="overlay-segmentation-mask.mp4",
        help="Filename for segmentation-mask overlay (default: overlay-segmentation-mask.mp4)",
    )
    parser.add_argument(
        "--render-mode",
        type=str,
        choices=["bbox", "mask", "both"],
        default="bbox",
        help="Overlay rendering mode: bbox, mask, or both (default: bbox)",
    )
    parser.add_argument(
        "--metadata-output-name",
        type=str,
        default="overlay-source.json",
        help="Filename for generation metadata (default: overlay-source.json)",
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=0.35,
        help="Fill alpha for overlay boxes in [0.0, 1.0] (default: 0.35)",
    )
    parser.add_argument(
        "--list-videos",
        action="store_true",
        help="List available videos with annotation track counts and exit",
    )
    return parser.parse_args()


def run_command(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=True, text=True, capture_output=True)


def probe_video(video_path: Path) -> dict[str, Any]:
    probe_cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,avg_frame_rate,nb_frames,duration",
        "-of",
        "json",
        str(video_path),
    ]
    output = run_command(probe_cmd)
    stream = json.loads(output.stdout)["streams"][0]

    width = int(stream["width"])
    height = int(stream["height"])

    rate_num, rate_den = map(int, stream["avg_frame_rate"].split("/"))
    fps = (rate_num / rate_den) if rate_den else 10.0

    nb_frames = stream.get("nb_frames")
    frame_count = int(nb_frames) if nb_frames else None

    duration = stream.get("duration")
    duration_s = float(duration) if duration else None

    return {
        "width": width,
        "height": height,
        "fps": fps,
        "frame_count": frame_count,
        "duration_s": duration_s,
    }


def build_filter_graph(
    tracks: list[dict[str, Any]],
    width: int,
    height: int,
    ann_width: int,
    ann_height: int,
    alpha: float,
) -> str:
    sx = width / ann_width
    sy = height / ann_height
    alpha = min(max(alpha, 0.0), 1.0)

    base_colors = ["red", "lime", "cyan", "yellow", "magenta", "orange"]
    filters: list[str] = []

    for track_index, track in enumerate(tracks):
        color_base = base_colors[track_index % len(base_colors)]
        color_fill = f"{color_base}@{alpha:.3f}"
        color_border = f"{color_base}@0.95"

        for frame_index, bbox in enumerate(track.get("bboxes", [])):
            if not bbox:
                continue
            x, y, w, h = bbox
            x_px = max(0, int(round(x * sx)))
            y_px = max(0, int(round(y * sy)))
            w_px = max(2, int(round(w * sx)))
            h_px = max(2, int(round(h * sy)))

            filters.append(
                "drawbox="
                f"x={x_px}:y={y_px}:w={w_px}:h={h_px}:"
                f"color={color_fill}:t=fill:enable='eq(n,{frame_index})'"
            )
            filters.append(
                "drawbox="
                f"x={x_px}:y={y_px}:w={w_px}:h={h_px}:"
                f"color={color_border}:t=3:enable='eq(n,{frame_index})'"
            )

    return ",".join(filters) if filters else "null"


def decode_uncompressed_rle(
    counts: list[int],
    height: int,
    width: int,
) -> np.ndarray:
    total = height * width
    flat = np.zeros(total, dtype=np.uint8)
    index = 0
    value = 0
    for count in counts:
        run = int(count)
        if run <= 0:
            value = 1 - value
            continue
        if value == 1:
            end = min(index + run, total)
            flat[index:end] = 1
        index += run
        if index >= total:
            break
        value = 1 - value
    return flat.reshape((height, width), order="F")


def decode_segmentation_mask(segmentation: Any) -> np.ndarray | None:
    if not segmentation:
        return None
    if not isinstance(segmentation, dict):
        return None
    counts = segmentation.get("counts")
    size = segmentation.get("size")
    if not isinstance(size, list) or len(size) != 2:
        return None
    if not isinstance(counts, list):
        # Compressed-RLE string is not expected in this dataset subset.
        return None
    height = int(size[0])
    width = int(size[1])
    return decode_uncompressed_rle(counts=counts, height=height, width=width)


def render_bbox_overlay_video(
    overlay_output: Path,
    width: int,
    height: int,
    fps: float,
    duration_s: float,
    tracks: list[dict[str, Any]],
    ann_width: int,
    ann_height: int,
    alpha: float,
) -> None:
    filter_graph = build_filter_graph(
        tracks=tracks,
        width=width,
        height=height,
        ann_width=ann_width,
        ann_height=ann_height,
        alpha=alpha,
    )

    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c=black:s={width}x{height}:r={fps}:d={duration_s:.6f}",
        "-vf",
        filter_graph,
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        str(overlay_output),
    ]
    subprocess.run(ffmpeg_cmd, check=True)


def render_segmentation_overlay_video(
    mask_output: Path,
    output_width: int,
    output_height: int,
    ann_width: int,
    ann_height: int,
    fps: float,
    frame_count: int,
    tracks: list[dict[str, Any]],
) -> None:
    palette = np.array(
        [
            [255, 80, 80],
            [80, 255, 80],
            [80, 220, 255],
            [255, 255, 80],
            [255, 80, 255],
            [255, 160, 80],
            [180, 120, 255],
        ],
        dtype=np.uint8,
    )

    frames = np.zeros((frame_count, ann_height, ann_width, 3), dtype=np.uint8)
    for track_index, track in enumerate(tracks):
        color = palette[track_index % len(palette)]
        segmentations = track.get("segmentations", [])
        max_frames = min(frame_count, len(segmentations))
        for frame_index in range(max_frames):
            mask = decode_segmentation_mask(segmentations[frame_index])
            if mask is None:
                continue
            if mask.shape != (ann_height, ann_width):
                continue
            frame = frames[frame_index]
            frame[mask > 0] = np.maximum(frame[mask > 0], color)

    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "rawvideo",
        "-pixel_format",
        "rgb24",
        "-video_size",
        f"{ann_width}x{ann_height}",
        "-framerate",
        f"{fps}",
        "-i",
        "-",
        "-vf",
        f"scale={output_width}:{output_height}:flags=neighbor",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        str(mask_output),
    ]
    process = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)
    try:
        assert process.stdin is not None
        for frame in frames:
            process.stdin.write(frame.tobytes())
    finally:
        if process.stdin is not None:
            process.stdin.close()
        return_code = process.wait()
        if return_code != 0:
            raise subprocess.CalledProcessError(return_code, ffmpeg_cmd)


def list_available_videos(
    videos: list[dict[str, Any]],
    annotations: list[dict[str, Any]],
) -> None:
    track_counts: dict[int, int] = defaultdict(int)
    for ann in annotations:
        track_counts[int(ann["video_id"])] += 1

    rows = []
    for video in videos:
        video_id = int(video["id"])
        name = video["file_names"][0].split("/")[0]
        rows.append((video_id, name, int(video["length"]), track_counts.get(video_id, 0)))
    rows.sort(key=lambda x: (-x[3], x[0]))

    print("video_id\tvideo_name\tframes\ttracks")
    for video_id, name, frame_count, tracks in rows:
        print(f"{video_id}\t{name}\t{frame_count}\t{tracks}")


def resolve_selected_video(
    videos: list[dict[str, Any]],
    video_name: str | None,
    video_id: int | None,
) -> dict[str, Any]:
    by_id = {int(video["id"]): video for video in videos}
    by_name = {video["file_names"][0].split("/")[0]: video for video in videos}

    selected: dict[str, Any] | None = None

    if video_name:
        selected = by_name.get(video_name)
        if selected is None:
            raise ValueError(f"Video name not found: {video_name}")
    if video_id is not None:
        selected_by_id = by_id.get(video_id)
        if selected_by_id is None:
            raise ValueError(f"Video id not found: {video_id}")
        if selected is not None and selected_by_id != selected:
            raise ValueError(
                "Provided --video-name and --video-id refer to different videos. "
                "Pass one selector or matching values."
            )
        selected = selected_by_id

    if selected is None:
        raise ValueError(
            "No video selected. Pass --video-name or --video-id, or use --list-videos."
        )

    return selected


def main() -> None:
    args = parse_args()

    dataset_root = args.dataset_root
    instances_json = args.instances_json or (dataset_root / "instances_50.json")
    videos_dir = args.videos_dir or (dataset_root / "videos")
    output_dir: Path = args.output_dir

    if not instances_json.exists():
        raise FileNotFoundError(f"instances json not found: {instances_json}")
    if not videos_dir.exists():
        raise FileNotFoundError(f"videos dir not found: {videos_dir}")

    data = json.loads(instances_json.read_text())
    videos: list[dict[str, Any]] = data["videos"]
    annotations: list[dict[str, Any]] = data["annotations"]

    if args.list_videos:
        list_available_videos(videos, annotations)
        return

    selected_video = resolve_selected_video(videos, args.video_name, args.video_id)
    selected_video_id = int(selected_video["id"])
    selected_video_name = selected_video["file_names"][0].split("/")[0]

    source_video = videos_dir / f"{selected_video_name}.mp4"
    if not source_video.exists():
        raise FileNotFoundError(f"source video not found: {source_video}")

    output_dir.mkdir(parents=True, exist_ok=True)
    base_output = output_dir / args.base_output_name
    overlay_output = output_dir / args.overlay_output_name
    mask_output = output_dir / args.mask_output_name
    metadata_output = output_dir / args.metadata_output_name

    shutil.copy2(source_video, base_output)

    probe = probe_video(base_output)
    width = int(probe["width"])
    height = int(probe["height"])
    fps = float(probe["fps"])
    frame_count = probe["frame_count"] or int(selected_video["length"])
    duration_s = probe["duration_s"] or (frame_count / fps)

    tracks = [ann for ann in annotations if int(ann["video_id"]) == selected_video_id]

    ann_width = int(selected_video["width"])
    ann_height = int(selected_video["height"])
    created_outputs: dict[str, str] = {"base": str(base_output)}
    if args.render_mode in {"bbox", "both"}:
        render_bbox_overlay_video(
            overlay_output=overlay_output,
            width=width,
            height=height,
            fps=fps,
            duration_s=duration_s,
            tracks=tracks,
            ann_width=ann_width,
            ann_height=ann_height,
            alpha=args.alpha,
        )
        created_outputs["bbox_overlay"] = str(overlay_output)

    if args.render_mode == "mask":
        render_segmentation_overlay_video(
            mask_output=overlay_output,
            output_width=width,
            output_height=height,
            ann_width=ann_width,
            ann_height=ann_height,
            fps=fps,
            frame_count=frame_count,
            tracks=tracks,
        )
        created_outputs["segmentation_mask_overlay"] = str(overlay_output)

    if args.render_mode == "both":
        render_segmentation_overlay_video(
            mask_output=mask_output,
            output_width=width,
            output_height=height,
            ann_width=ann_width,
            ann_height=ann_height,
            fps=fps,
            frame_count=frame_count,
            tracks=tracks,
        )
        created_outputs["segmentation_mask_overlay"] = str(mask_output)

    metadata_output.write_text(
        json.dumps(
            {
                "dataset_root": str(dataset_root),
                "instances_json": str(instances_json),
                "videos_dir": str(videos_dir),
                "video_name": selected_video_name,
                "video_id": selected_video_id,
                "tracks": len(tracks),
                "annotation_size": {"width": ann_width, "height": ann_height},
                "output_size": {"width": width, "height": height},
                "fps": fps,
                "frames": frame_count,
                "render_mode": args.render_mode,
                "outputs": created_outputs,
                "type": "youtube_vis_overlay",
            },
            indent=2,
        )
    )

    print(f"Generated base video: {base_output}")
    if args.render_mode == "bbox":
        print(f"Generated bbox overlay video: {overlay_output}")
    elif args.render_mode == "mask":
        print(f"Generated segmentation-mask video: {overlay_output}")
    elif "bbox_overlay" in created_outputs:
        print(f"Generated bbox overlay video: {overlay_output}")
    if args.render_mode == "both" and "segmentation_mask_overlay" in created_outputs:
        print(f"Generated segmentation-mask video: {mask_output}")
    print(f"Generated metadata: {metadata_output}")


if __name__ == "__main__":
    main()
