# Automated video → curated frames pipeline

This example shows how to run videos through LightlyStudio fully automatically and write
**curated extracted frames** back to storage (e.g. S3). It targets the workflow where new
videos arrive continuously, old ones are deleted by a retention policy, and the deliverable
is a deduplicated, content-rich set of frames per video.

It treats the frames as a normal **image dataset** (no video dataset, no GUI needed).

## What it does

For every new video in the input location, the pipeline:

1. **Extracts frames** from every new video sub-sampled to a target frame rate, via the
   `ImageDataset.add_frames_from_videos(...)` API.
2. **Drops low-content / corrupt frames** using a row-uniformity metric
   (`row_uniformity.compute_uniform_row_ratio`, ported from LightlyOne's `uniformRowRatio`).
   Higher score ⇒ more uniform / blank, so only frames with score ≤ `uniform_row_ratio_max`
   are kept.
3. **Deduplicates** the remaining frames with embedding-based deduplication sampling
   (diversity selection with a minimum-distance stopping condition). The selected frames are
   marked with the `deduplicated` tag (visible in the GUI), which sampling creates. The tag
   is re-created each run, so it reflects the most recent run's selection.
4. **Uploads** the selected frames to `output_uri/<video_stem>/`.

## Incremental processing (only new videos)

The pipeline connects to a **persistent** LightlyStudio database. Because
`add_frames_from_videos` always tags a video's frames with the video file stem and skips
videos whose stem tag already exists, re-running the pipeline only processes videos added
since the last run. A video that produced zero selected frames still has its stem tag and is
therefore never reprocessed.

> **Important:** the database must live on **durable storage**. Use a DuckDB file on a
> persistent volume, or point LightlyStudio at Postgres for a production deployment
> (set `LIGHTLY_STUDIO_DATABASE_URL=postgresql://user:pass@host:5432/db` and remove the
> `--db-file` argument). If the database is lost, all videos look new again.

## Run it locally

```bash
cd video_frame_curation

python pipeline.py \
    --input-uri s3://my-input-bucket/videos/ \
    --output-uri s3://my-output-bucket/curated-frames/ \
    --db-file ./video_frame_curation.duckdb \
    --extract-dir ./video_frame_curation_frames \
    --fps 1 \
    --uniform-row-ratio-max 0.025 \
    --dedup-min-distance 0.2
```

Inspect the results in the GUI (point it at the same database). Frames are kept in
`--extract-dir`, and the selected frames carry the `deduplicated` tag.

Equivalently, configure it via environment variables:

| Variable | Meaning |
| --- | --- |
| `VIDEO_CURATION_INPUT_URI` | Location of the input videos (e.g. `s3://bucket/videos/`). |
| `VIDEO_CURATION_OUTPUT_URI` | Location the curated frames are written to. |
| `VIDEO_CURATION_DB_FILE` | Path to the persistent DuckDB file. |
| `VIDEO_CURATION_EXTRACT_DIR` | Persistent local directory for extracted frames. |

S3 access uses the standard AWS credential resolution (`AWS_ACCESS_KEY_ID`,
`AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, or an instance/role profile).

## Schedule it with Airflow

Copy `pipeline.py`, `row_uniformity.py`, and `airflow_dag.py` into your Airflow `dags/`
folder, install Airflow in the worker environment, and set the `VIDEO_CURATION_*`
environment variables. The DAG (`video_frame_curation`) runs `@weekly` and simply executes
`pipeline.py` (via a `BashOperator`). Airflow is intentionally **not** a dependency of
LightlyStudio.

## Curation knobs

| Argument | Default | Effect |
| --- | --- | --- |
| `--fps` | `1` | Frames per second to extract from each video. |
| `--uniform-row-ratio-max` | `0.025` | Max row-uniformity score to keep a frame (higher ⇒ more uniform/corrupt). |
| `--dedup-min-distance` | `0.2` | Deduplication stopping distance; larger ⇒ fewer, more diverse frames. |

## Known limitations / TODOs

- **Local disk usage:** frames are materialized to a persistent local directory
  (`--extract-dir`) and kept there, since the database references those files. This assumes
  local disk is available and accumulates over time. A future improvement is a disk-free /
  streaming path (decode → embed → discard).
- **Database growth:** the persistent database accumulates frame samples over time. A future
  improvement is to prune the non-selected frame samples after upload while keeping the
  per-video stem tag as the durable processed-marker.
- **Deduplication scope:** all new frames in a run are deduplicated together (across the
  videos added since the last run), but not against frames from previous runs.
