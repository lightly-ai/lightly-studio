"""Example Airflow DAG that runs the video-frame curation pipeline on a schedule.

Drop this file (together with ``pipeline.py`` and ``row_uniformity.py``) into your Airflow
``dags/`` folder. The DAG runs weekly and processes only the videos that are new since the
previous run. Airflow is not a dependency of LightlyStudio; install it separately in the
environment that runs the scheduler/workers.

``pipeline.py`` is a plain script, so the DAG just runs it. Configure it via environment
variables (see ``README.md``):
- ``VIDEO_CURATION_INPUT_URI``   - location of the input videos, e.g. ``s3://bucket/videos/``
- ``VIDEO_CURATION_OUTPUT_URI``  - location for the curated frames
- ``VIDEO_CURATION_DB_FILE``     - path to the persistent DuckDB file (durable storage!)
- ``VIDEO_CURATION_EXTRACT_DIR`` - persistent dir for extracted frames (durable storage!)
"""

from __future__ import annotations

import os
from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator

PIPELINE_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pipeline.py")

with DAG(
    dag_id="video_frame_curation",
    description="Extract, filter and deduplicate frames from new videos into curated frames.",
    start_date=datetime(2026, 1, 1),
    schedule="@weekly",
    catchup=False,
) as dag:
    BashOperator(
        task_id="curate_video_frames",
        bash_command=f"python {PIPELINE_SCRIPT}",
    )
