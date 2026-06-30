"""Example of how to query, tag, sample, and export individual video frames.

It opens a video dataset, queries its frames by frame-level fields, tags the matches,
runs a sampling strategy on the query, and exports the sampled frames as
`(frame_number, frame_timestamp_s)` rows to a CSV file.
"""

from __future__ import annotations

import csv
import tempfile
from pathlib import Path

from environs import Env

import lightly_studio as ls
from lightly_studio.core.dataset_query import VideoFrameSampleField
from lightly_studio.database import db_manager

env = Env()
env.read_env()
db_manager.connect(cleanup_existing=True)
dataset_path = env.path("EXAMPLES_VIDEO_DATASET_PATH", "/path/to/your/dataset")

dataset = ls.VideoDataset.create()
dataset.add_videos_from_path(path=dataset_path, embed=False, target_fps=1)

frames = dataset.frames()
print(f"\nTotal frames in dataset: {len(list(frames))}")

# Filtering by a frame-level field (frame_number) works
min_frame_number = 3
selected = frames.match(VideoFrameSampleField.frame_number > min_frame_number)
print(
    f"\nFiltering by fields: There are {len(selected.to_list())} frames after frame "
    f"{min_frame_number}."
)

# Writing metadata for all frames in a query works
for frame in frames.match(VideoFrameSampleField.frame_number > 1):
    frame.metadata["score"] = float(frame.frame_number)
print("\nAdded metadata to frames with frame_number > 1.")


# Sampling works
frames.match(VideoFrameSampleField.frame_number > 1).sampling().metadata_weighting(
    n_samples_to_select=5,
    sampling_result_tag_name="sampled",
    metadata_key="score",
)
print("\nSampled the 5 frames with the highest metadata.score value.")

# Export the sampled frames as (frame_number, frame_timestamp_s) rows to a CSV file.
out_csv = Path(tempfile.gettempdir()) / "sampled_video_frames.csv"
with out_csv.open("w", newline="") as fh:
    writer = csv.writer(fh)
    writer.writerow(["frame_number", "frame_timestamp_s"])
    for frame in frames.match(VideoFrameSampleField.tags.contains("sampled")):
        writer.writerow([frame.frame_number, frame.frame_timestamp_s])

print(f"\nExported sampled frames to {out_csv}")
print(f"First 3 lines: {list(out_csv.read_text().splitlines())[:3]}")
