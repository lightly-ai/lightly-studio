#!/usr/bin/env python3
"""Fill missing transcripts for pulled videos with faster-whisper.

Some deliveries (e.g. the Deepen bucket) arrive as a video with no transcript companion.
This step closes that gap: for every pulled delivery whose transcript is missing, it runs
``scripts/transcribe_with_faster_whisper.py`` to write a faster-whisper JSON next to the
video, then returns the deliveries with their transcript paths resolved.

Faster Whisper lives in its own virtual environment (it is deliberately not a project
dependency), so this step shells out to that environment's Python via a jobs manifest
rather than importing it -- the same pattern ``run_egocentric_qa`` uses.
"""

from __future__ import annotations

import dataclasses
import json
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING or __package__:
    from scripts import qa_pull
else:
    import qa_pull

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_REPOSITORY_ROOT = _PROJECT_ROOT.parent
# Mirror run_egocentric_qa so the same whisper virtual environment and worker are reused.
DEFAULT_WHISPER_PYTHON = _REPOSITORY_ROOT / "test" / "whisper-env" / "bin" / "python"
WHISPER_WORKER_PATH = _PROJECT_ROOT / "scripts" / "transcribe_with_faster_whisper.py"
DEFAULT_WHISPER_MODEL = "turbo"
DEFAULT_WHISPER_DEVICE = "auto"
DEFAULT_WHISPER_COMPUTE_TYPE = "default"
TRANSCRIPT_SUFFIX = ".faster-whisper.json"


def fill_missing_transcripts(
    triplets: list[qa_pull.LocalTriplet],
    whisper_python: Path = DEFAULT_WHISPER_PYTHON,
    model: str = DEFAULT_WHISPER_MODEL,
    device: str = DEFAULT_WHISPER_DEVICE,
    compute_type: str = DEFAULT_WHISPER_COMPUTE_TYPE,
) -> list[qa_pull.LocalTriplet]:
    """Transcribe every delivery whose transcript is missing and resolve its path.

    Args:
        triplets: Pulled deliveries, some possibly without a transcript.
        whisper_python: Python executable of the faster-whisper virtual environment.
        model: Faster Whisper model name.
        device: CTranslate2 device (``auto``, ``cuda``, or ``cpu``).
        compute_type: CTranslate2 compute type.

    Returns:
        The deliveries with ``transcript_path`` set for every video, in input order.

    Raises:
        FileNotFoundError: If transcripts must be generated but the whisper Python is
            not present, so the caller learns the environment is not set up.
    """
    missing = [triplet for triplet in triplets if triplet.transcript_path is None]
    if not missing:
        return list(triplets)
    if not whisper_python.is_file():
        raise FileNotFoundError(
            f"Whisper Python executable does not exist: '{whisper_python}'. "
            f"{len(missing)} video(s) need a transcript; pass a valid --whisper-python."
        )

    output_by_key = {_key(triplet): _transcript_output_path(triplet) for triplet in missing}
    _run_whisper(
        jobs=[
            {
                "video_path": str(triplet.video_path),
                "output_path": str(output_by_key[_key(triplet)]),
            }
            for triplet in missing
        ],
        whisper_python=whisper_python,
        model=model,
        device=device,
        compute_type=compute_type,
    )

    return [
        (
            dataclasses.replace(
                triplet,
                transcript_path=output_by_key[_key(triplet)],
                local_files=(*triplet.local_files, output_by_key[_key(triplet)]),
            )
            if triplet.transcript_path is None
            else triplet
        )
        for triplet in triplets
    ]


def _transcript_output_path(triplet: qa_pull.LocalTriplet) -> Path:
    """Return where the generated transcript is written, alongside its video."""
    return triplet.video_path.with_name(triplet.video_path.stem + TRANSCRIPT_SUFFIX)


def _key(triplet: qa_pull.LocalTriplet) -> tuple[str, str]:
    return (triplet.bucket, triplet.stem)


def _run_whisper(
    jobs: list[dict[str, str]],
    whisper_python: Path,
    model: str,
    device: str,
    compute_type: str,
) -> None:
    """Write the jobs manifest and run the faster-whisper worker over it."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", prefix="whisper_jobs_", delete=False, encoding="utf-8"
    ) as handle:
        json.dump(jobs, handle, indent=2)
        jobs_path = Path(handle.name)
    try:
        subprocess.run(
            [
                str(whisper_python.absolute()),
                str(WHISPER_WORKER_PATH),
                "--jobs",
                str(jobs_path),
                "--model",
                model,
                "--device",
                device,
                "--compute-type",
                compute_type,
            ],
            check=True,
        )
    finally:
        jobs_path.unlink(missing_ok=True)
