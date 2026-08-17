"""Optional faster-whisper transcription for missing delivery transcripts."""

from __future__ import annotations

import dataclasses
import json
import subprocess
import tempfile
from pathlib import Path

from auto_qa.storage import LocalDelivery

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
DEFAULT_PYTHON = REPOSITORY_ROOT / "test" / "whisper-env" / "bin" / "python"
WORKER = PROJECT_ROOT / "scripts" / "transcribe_with_faster_whisper.py"
DEFAULT_MODEL = "turbo"
DEFAULT_DEVICE = "auto"
DEFAULT_COMPUTE_TYPE = "default"


def missing_transcripts(
    deliveries: list[LocalDelivery],
    python: Path = DEFAULT_PYTHON,
    model: str = DEFAULT_MODEL,
    device: str = DEFAULT_DEVICE,
    compute_type: str = DEFAULT_COMPUTE_TYPE,
) -> list[LocalDelivery]:
    """Generate and attach transcripts for deliveries that lack one."""
    missing = [delivery for delivery in deliveries if delivery.transcript_path is None]
    if not missing:
        return deliveries
    if not python.is_file():
        raise FileNotFoundError(f"Whisper Python does not exist: '{python}'.")

    outputs = {delivery: _output_path(delivery) for delivery in missing}
    jobs = [
        {"video_path": str(delivery.video_path), "output_path": str(outputs[delivery])}
        for delivery in missing
    ]
    _run(jobs=jobs, python=python, model=model, device=device, compute_type=compute_type)
    return [
        dataclasses.replace(
            delivery,
            transcript_path=outputs[delivery],
            local_files=(*delivery.local_files, outputs[delivery]),
        )
        if delivery in outputs
        else delivery
        for delivery in deliveries
    ]


def _output_path(delivery: LocalDelivery) -> Path:
    return delivery.video_path.with_name(f"{delivery.video_path.stem}.faster-whisper.json")


def _run(
    jobs: list[dict[str, str]],
    python: Path,
    model: str,
    device: str,
    compute_type: str,
) -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as handle:
        json.dump(jobs, handle)
        jobs_path = Path(handle.name)
    try:
        subprocess.run(
            [
                str(python.absolute()),
                str(WORKER),
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
