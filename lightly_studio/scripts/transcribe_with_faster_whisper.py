"""Transcribe videos with Faster Whisper, word timestamps, and Silero VAD.

This worker intentionally depends only on ``faster-whisper`` and the Python standard
library. It runs inside a dedicated Whisper virtual environment while the calling
LightlyStudio workflow runs in the project's ``uv`` environment.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter
from typing import Any

from faster_whisper import WhisperModel  # type: ignore[import-untyped]


def transcribe_jobs(  # noqa: PLR0913
    *,
    jobs_path: Path,
    model_name: str,
    device: str,
    compute_type: str,
    beam_size: int,
    vad_enabled: bool,
    vad_threshold: float,
    vad_min_silence_ms: int,
) -> None:
    """Load Faster Whisper once and transcribe all jobs in a manifest.

    Args:
        jobs_path: JSON list containing ``video_path`` and ``output_path`` values.
        model_name: Faster Whisper model name.
        device: CTranslate2 device, such as ``auto``, ``cuda``, or ``cpu``.
        compute_type: CTranslate2 compute type, such as ``default`` or ``float16``.
        beam_size: Number of beams used during decoding.
        vad_enabled: Whether to remove silence with Silero VAD before transcription.
        vad_threshold: Silero speech-probability threshold.
        vad_min_silence_ms: Silence duration that separates speech chunks.
    """
    if beam_size < 1:
        raise ValueError(f"beam_size must be at least 1, got {beam_size}.")
    if not 0.0 <= vad_threshold <= 1.0:
        raise ValueError(f"vad_threshold must be in [0, 1], got {vad_threshold}.")
    if vad_min_silence_ms < 0:
        raise ValueError(f"vad_min_silence_ms must be non-negative, got {vad_min_silence_ms}.")
    jobs = _load_jobs(jobs_path=jobs_path)
    print(
        f"Loading Faster Whisper model {model_name} on {device} ({compute_type})...",
        flush=True,
    )
    start_time = perf_counter()
    model = WhisperModel(
        model_name,
        device=device,
        compute_type=compute_type,
    )
    print(f"Loaded Faster Whisper model in {perf_counter() - start_time:.2f}s.", flush=True)
    for index, job in enumerate(jobs, start=1):
        print(f"Starting transcription {index}/{len(jobs)}.", flush=True)
        _transcribe_job(
            model=model,
            video_path=Path(job["video_path"]),
            output_path=Path(job["output_path"]),
            model_name=model_name,
            beam_size=beam_size,
            vad_enabled=vad_enabled,
            vad_threshold=vad_threshold,
            vad_min_silence_ms=vad_min_silence_ms,
        )


def _transcribe_job(  # noqa: PLR0913
    *,
    model: WhisperModel,
    video_path: Path,
    output_path: Path,
    model_name: str,
    beam_size: int,
    vad_enabled: bool,
    vad_threshold: float,
    vad_min_silence_ms: int,
) -> None:
    print(f"Transcribing {video_path.name} with Faster Whisper {model_name}...", flush=True)
    start_time = perf_counter()
    segments_iter, info = model.transcribe(
        str(video_path),
        beam_size=beam_size,
        word_timestamps=True,
        vad_filter=vad_enabled,
        vad_parameters={
            "threshold": vad_threshold,
            "min_silence_duration_ms": vad_min_silence_ms,
        },
        log_progress=True,
    )
    # Faster Whisper returns a lazy generator; iteration performs the transcription.
    segments = list(segments_iter)
    normalized_segments = [_normalize_segment(segment=segment) for segment in segments]
    min_silence_s = vad_min_silence_ms / 1000.0
    silences = _detect_silences(
        segments=normalized_segments,
        duration_s=float(info.duration),
        min_silence_s=min_silence_s,
    )
    result = {
        "engine": "faster-whisper",
        "model": model_name,
        "text": " ".join(segment["text"] for segment in normalized_segments).strip(),
        "language": info.language,
        "language_probability": float(info.language_probability),
        "duration_s": float(info.duration),
        "speech_duration_s": float(info.duration_after_vad),
        "vad_enabled": vad_enabled,
        "vad_threshold": vad_threshold,
        "vad_min_silence_ms": vad_min_silence_ms,
        "silences": silences,
        "segments": normalized_segments,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        f"Wrote transcript for {video_path.name} in {perf_counter() - start_time:.2f}s.",
        flush=True,
    )


def _normalize_segment(segment: Any) -> dict[str, Any]:
    words = [
        {
            "word": word.word,
            "start": float(word.start),
            "end": float(word.end),
            "probability": float(word.probability),
        }
        for word in (segment.words or [])
    ]
    return {
        "text": segment.text.strip(),
        "start": float(segment.start),
        "end": float(segment.end),
        "avg_logprob": float(segment.avg_logprob),
        "no_speech_prob": float(segment.no_speech_prob),
        "words": words,
    }


def _detect_silences(
    *,
    segments: list[dict[str, Any]],
    duration_s: float,
    min_silence_s: float,
) -> list[dict[str, float]]:
    silences = []
    previous_end_s = 0.0
    for segment in segments:
        start_time_s = float(segment["start"])
        if start_time_s - previous_end_s >= min_silence_s:
            silences.append(_silence(start_time_s=previous_end_s, end_time_s=start_time_s))
        previous_end_s = max(previous_end_s, float(segment["end"]))
    if duration_s - previous_end_s >= min_silence_s:
        silences.append(_silence(start_time_s=previous_end_s, end_time_s=duration_s))
    return silences


def _silence(*, start_time_s: float, end_time_s: float) -> dict[str, float]:
    return {
        "start": start_time_s,
        "end": end_time_s,
        "duration": end_time_s - start_time_s,
    }


def _load_jobs(jobs_path: Path) -> list[dict[str, str]]:
    payload: Any = json.loads(jobs_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Whisper jobs manifest must be a JSON list.")

    jobs: list[dict[str, str]] = []
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("Each Whisper job must be a JSON object.")
        video_path = item.get("video_path")
        output_path = item.get("output_path")
        if not isinstance(video_path, str) or not isinstance(output_path, str):
            raise ValueError("Each Whisper job needs string video_path and output_path values.")
        jobs.append({"video_path": video_path, "output_path": output_path})
    return jobs


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=Path, required=True, help="Path to the jobs JSON manifest.")
    parser.add_argument("--model", default="turbo", help="Faster Whisper model name.")
    parser.add_argument("--device", default="auto", help="CTranslate2 device: auto, cuda, or cpu.")
    parser.add_argument("--compute-type", default="default", help="CTranslate2 compute type.")
    parser.add_argument("--beam-size", type=int, default=5)
    parser.add_argument("--disable-vad", action="store_true")
    parser.add_argument("--vad-threshold", type=float, default=0.5)
    parser.add_argument("--vad-min-silence-ms", type=int, default=500)
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    transcribe_jobs(
        jobs_path=args.jobs,
        model_name=args.model,
        device=args.device,
        compute_type=args.compute_type,
        beam_size=args.beam_size,
        vad_enabled=not args.disable_vad,
        vad_threshold=args.vad_threshold,
        vad_min_silence_ms=args.vad_min_silence_ms,
    )
