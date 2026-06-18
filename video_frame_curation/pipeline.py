"""Automated video -> curated frames pipeline.

For the new videos in an input location this script:
1. extracts frames (sub-sampled to a target fps),
2. drops low-content / corrupt frames using a row-uniformity metric,
3. deduplicates the remaining frames by embedding distance, and
4. uploads the selected frames to an output location.

It is designed to run repeatedly (e.g. weekly via cron / Airflow). It connects to a
**persistent** LightlyStudio database and only processes new videos: because
``ImageDataset.add_frames_from_videos`` tags every video's frames with the video stem and
skips videos whose stem tag already exists, re-running only processes videos added since the
last run. A video that produced zero selected frames still has its stem tag, so it is never
reprocessed.

Run it directly:

    python pipeline.py \\
        --input-uri s3://my-input-bucket/videos/ \\
        --output-uri s3://my-output-bucket/curated-frames/ \\
        --db-file ./video_frame_curation.duckdb

or configure it via the ``VIDEO_CURATION_*`` environment variables (see ``README.md``).
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

import fsspec
from PIL import Image

import lightly_studio as ls
from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.core.image.image_sample import ImageSample
from lightly_studio.database import db_manager
from lightly_studio.resolvers import tag_resolver
from lightly_studio.sampling.sample import Sampling
from row_uniformity import compute_uniform_row_ratio

logger = logging.getLogger(__name__)

DATASET_NAME = "video_frame_curation"
UNIFORM_ROW_RATIO_KEY = "uniform_row_ratio"
# GUI-visible tag holding the frames selected by deduplication. Sampling creates it; it is
# re-created on each run (sampling requires an unused tag name), so it reflects the latest run.
SELECTED_TAG = "deduplicated"


def parse_args() -> argparse.Namespace:
    """Parse the pipeline configuration, defaulting to the ``VIDEO_CURATION_*`` env vars."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--input-uri",
        default=os.environ.get("VIDEO_CURATION_INPUT_URI"),
        help="Location holding the input videos (e.g. s3://bucket/videos/).",
    )
    parser.add_argument(
        "--output-uri",
        default=os.environ.get("VIDEO_CURATION_OUTPUT_URI"),
        help="Location the selected frames are written to.",
    )
    parser.add_argument(
        "--db-file",
        default=os.environ.get("VIDEO_CURATION_DB_FILE", "./video_frame_curation.duckdb"),
        help="Path to the persistent DuckDB file (must be on durable storage).",
    )
    parser.add_argument(
        "--extract-dir",
        default=os.environ.get("VIDEO_CURATION_EXTRACT_DIR", "./video_frame_curation_frames"),
        help=(
            "Persistent local directory for extracted frames. The database references these "
            "files, so they must stay on disk for the GUI to display them."
        ),
    )
    parser.add_argument(
        "--fps", type=float, default=1.0, help="Frames per second to extract from each video."
    )
    parser.add_argument(
        "--uniform-row-ratio-max",
        type=float,
        default=0.025,
        help="Keep only frames whose row-uniformity score is <= this (higher = more uniform).",
    )
    parser.add_argument(
        "--dedup-min-distance",
        type=float,
        default=0.2,
        help="Deduplication stopping distance; larger => fewer, more diverse frames.",
    )
    args = parser.parse_args()
    if not args.input_uri or not args.output_uri:
        parser.error(
            "input and output locations are required "
            "(--input-uri/--output-uri or VIDEO_CURATION_INPUT_URI/VIDEO_CURATION_OUTPUT_URI)."
        )
    return args


def run_pipeline(
    input_uri: str,
    output_uri: str,
    db_file: str,
    extract_dir: str,
    fps: float,
    uniform_row_ratio_max: float,
    dedup_min_distance: float,
) -> None:
    """Process all not-yet-processed videos from ``input_uri`` into ``output_uri``."""
    # Reset any engine from a previous invocation so repeated runs in a long-lived worker
    # (e.g. an Airflow worker) reconnect cleanly to the persistent database.
    db_manager.close()
    db_manager.connect(db_file=db_file)
    dataset = ls.ImageDataset.load_or_create(name=DATASET_NAME)

    # Extract frames from all new videos in one pass. Already-processed videos (whose stem
    # tag exists) are skipped, and every frame is tagged with its video stem.
    new_ids = dataset.add_frames_from_videos(
        videos_path=input_uri, extract_dir=Path(extract_dir), fps=fps, embed=True
    )
    if not new_ids:
        logger.info("No new videos to process in %s.", input_uri)
        return
    logger.info("Extracted %d frames from new videos.", len(new_ids))

    # Drop low-content / corrupt frames using the row-uniformity metric.
    kept_ids = _add_row_uniformity_and_filter(
        dataset=dataset, sample_ids=new_ids, uniform_row_ratio_max=uniform_row_ratio_max
    )
    logger.info("Kept %d/%d frames after row-uniformity filter.", len(kept_ids), len(new_ids))
    if not kept_ids:
        return

    # Deduplicate the kept frames together and upload the selection.
    selected = _deduplicate(
        dataset=dataset, kept_ids=kept_ids, dedup_min_distance=dedup_min_distance
    )
    logger.info("Selected %d frames after deduplication.", len(selected))
    _upload_frames(samples=selected, output_uri=output_uri)


def _add_row_uniformity_and_filter(
    dataset: ls.ImageDataset,
    sample_ids: list,
    uniform_row_ratio_max: float,
) -> list:
    """Store the row-uniformity metric per frame and return the ids of content-rich frames."""
    sample_metadata = []
    kept_ids = []
    for sample_id in sample_ids:
        sample = dataset.get_sample(sample_id)
        with Image.open(sample.file_path_abs) as image:
            ratio = compute_uniform_row_ratio(image_greyscale=image.convert("L"))
        sample_metadata.append((sample_id, {UNIFORM_ROW_RATIO_KEY: ratio}))
        if ratio <= uniform_row_ratio_max:
            kept_ids.append(sample_id)

    dataset.update_metadata(sample_metadata)
    return kept_ids


def _deduplicate(
    dataset: ls.ImageDataset, kept_ids: list, dedup_min_distance: float
) -> list[ImageSample]:
    """Deduplicate this run's kept frames; the selection is tagged ``deduplicated``.

    Sampling runs directly on ``kept_ids`` and creates the result tag itself. The tag is
    cleared first because sampling requires an unused tag name, so it reflects the latest run.
    """
    _delete_tag(dataset=dataset, tag_name=SELECTED_TAG)
    Sampling(
        dataset_id=dataset.collection_id,
        session=dataset.session,
        input_sample_ids=kept_ids,
    ).deduplicate(
        n_samples_to_select=len(kept_ids),
        sampling_result_tag_name=SELECTED_TAG,
        stopping_condition_minimum_distance=dedup_min_distance,
    )
    return dataset.query().match(ImageSampleField.tags.contains(SELECTED_TAG)).to_list()


def _upload_frames(samples: list[ImageSample], output_uri: str) -> None:
    """Upload the given frames to ``output_uri/<video_stem>/`` via fsspec.

    The video stem is recovered from the frame's parent directory (frames are extracted into
    one subdirectory per video).
    """
    out_fs, out_base = fsspec.core.url_to_fs(output_uri)
    base = out_base.rstrip("/")
    created_dirs: set[str] = set()
    for sample in samples:
        video_stem = Path(sample.file_path_abs).parent.name
        dest_dir = f"{base}/{video_stem}"
        if dest_dir not in created_dirs:
            out_fs.makedirs(dest_dir, exist_ok=True)
            created_dirs.add(dest_dir)
        out_fs.put_file(sample.file_path_abs, f"{dest_dir}/{sample.file_name}")


def _delete_tag(dataset: ls.ImageDataset, tag_name: str) -> None:
    tag = tag_resolver.get_by_name(
        session=dataset.session, tag_name=tag_name, collection_id=dataset.collection_id
    )
    if tag is not None:
        tag_resolver.delete(session=dataset.session, tag_id=tag.tag_id)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cli_args = parse_args()
    run_pipeline(
        input_uri=cli_args.input_uri,
        output_uri=cli_args.output_uri,
        db_file=cli_args.db_file,
        extract_dir=cli_args.extract_dir,
        fps=cli_args.fps,
        uniform_row_ratio_max=cli_args.uniform_row_ratio_max,
        dedup_min_distance=cli_args.dedup_min_distance,
    )
