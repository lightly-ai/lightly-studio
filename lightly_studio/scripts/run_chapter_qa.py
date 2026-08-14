"""Benchmark full-transcript chapter QA against cached Whisper transcripts.

Reads the ``text`` field of each transcript JSON, asks the model to split it into chapters in one
call per video, derives task/environment share and a repetition flag, and reports wall-clock
throughput. This is the standalone harness for eyeballing chapter quality and single-GPU speed on
Ollama before wiring the chapter path into the main pipeline.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from tqdm import tqdm

from lightly_studio.dataset import chapter_classification

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TRANSCRIPTS = REPOSITORY_ROOT / "test" / "transcripts"
DEFAULT_OUTPUT = REPOSITORY_ROOT / "test" / "chapter_qa_results.json"
DEFAULT_BASE_URL = os.environ.get("NARRATION_LLM_BASE_URL", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("NARRATION_LLM_MODEL", "qwen3:8b")
DEFAULT_PROVIDER = os.environ.get("NARRATION_LLM_PROVIDER", "ollama")
DEFAULT_API_KEY = os.environ.get("NARRATION_LLM_API_KEY")


def run(args: argparse.Namespace) -> None:
    """Classify transcripts into chapters and write a results report.

    Args:
        args: Parsed command-line arguments.
    """
    transcripts = _load_transcripts(directory=args.transcripts.resolve(), limit=args.limit)
    if not transcripts:
        raise FileNotFoundError(f"No transcript JSON found under: '{args.transcripts}'.")
    classifier = chapter_classification.ChapterClassifier(
        settings=chapter_classification.ChapterClassifierSettings(
            base_url=args.base_url,
            model=args.model,
            provider=args.provider,
            api_key=args.api_key,
        )
    )
    texts_by_key = [(name, text) for name, text, _ in transcripts]
    text_by_key = {name: text for name, text, _ in transcripts}

    print(
        f"Classifying {len(transcripts)} transcript(s) with {args.model} "
        f"({args.provider}) at {args.base_url}, max_workers={args.max_workers}...",
        flush=True,
    )
    progress = tqdm(total=len(transcripts), desc="Chaptering", unit="video", dynamic_ncols=True)

    def on_complete(_: str) -> None:
        progress.update(1)

    start_time = time.monotonic()
    chapters_by_key = classifier.classify_many(
        texts_by_key=texts_by_key,
        max_workers=args.max_workers,
        on_complete=on_complete,
    )
    elapsed_s = time.monotonic() - start_time
    progress.close()

    records = [
        _build_record(name=name, text=text_by_key[name], chapters=chapters)
        for name, chapters in chapters_by_key.items()
    ]
    records.sort(key=lambda record: record["file"])
    failed = [name for name, _ in texts_by_key if name not in chapters_by_key]
    args.output.write_text(json.dumps(records, indent=2), encoding="utf-8")
    _print_report(records=records, failed=failed, elapsed_s=elapsed_s, output=args.output)


def _load_transcripts(directory: Path, limit: int | None) -> list[tuple[str, str, Path]]:
    if not directory.is_dir():
        raise FileNotFoundError(f"Transcript directory does not exist: '{directory}'.")
    transcripts: list[tuple[str, str, Path]] = []
    for path in sorted(directory.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(payload, dict):
            continue
        text = str(payload.get("text", "")).strip()
        if text:
            transcripts.append((path.name, text, path))
    if limit is not None:
        transcripts = transcripts[:limit]
    return transcripts


def _build_record(
    name: str,
    text: str,
    chapters: list[chapter_classification.TranscriptChapter],
) -> dict[str, Any]:
    summary = chapter_classification.summarize_chapters(text=text, chapters=chapters)
    record = {"file": name}
    record.update(chapter_classification.summary_to_dict(summary=summary))
    return record


def _print_report(
    records: list[dict[str, Any]],
    failed: list[str],
    elapsed_s: float,
    output: Path,
) -> None:
    print()
    header = f"{'file':<48} {'task%':>6} {'env%':>6} {'qual%':>6} {'rep':>5} {'status':<14}"
    print(header)
    print("-" * len(header))
    for record in records:
        print(
            f"{record['file'][:48]:<48} "
            f"{record['task_percentage']:>6.1f} "
            f"{record['environment_percentage']:>6.1f} "
            f"{record['qualifying_percentage']:>6.1f} "
            f"{'YES' if record['is_repetitive'] else '-':>5} "
            f"{record['status']:<14}"
        )
    processed = len(records)
    per_video = elapsed_s / processed if processed else 0.0
    print()
    print(
        f"Processed {processed} video(s) in {elapsed_s:.1f}s "
        f"({per_video:.2f}s/video). Failed: {len(failed)}."
    )
    if failed:
        print(f"  Failed files: {', '.join(failed)}")
    print(f"Wrote results to {output}.")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transcripts", type=Path, default=DEFAULT_TRANSCRIPTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--provider", choices=("ollama", "openai"), default=DEFAULT_PROVIDER)
    parser.add_argument("--api-key", default=DEFAULT_API_KEY)
    parser.add_argument(
        "--max-workers",
        type=int,
        default=chapter_classification.DEFAULT_MAX_WORKERS,
        help="Concurrent requests in flight; match the server's parallelism ceiling.",
    )
    parser.add_argument("--limit", type=int, default=None)
    return parser.parse_args()


if __name__ == "__main__":
    run(args=_parse_args())
