"""Benchmark the COCO loaders against the Caltech UX run data on S3 (friction rows 8 and 40).

Times two steps on a throwaway DuckDB file, with embeddings off:

1. `add_samples_from_coco` with `labels_noisy.json` and images on S3.
2. `add_annotations_from_coco` with the model v1 predictions, restricted to the loaded images.

Hosted LightlyStudio stores data in a remote Postgres, so every SQL statement costs a network
round trip. `--db-rtt-ms` adds a sleep per statement to model that. The script also counts SQL
statements and S3 metadata calls (`exists`/`info`) per step.

Usage (from lightly_studio/):
    AWS_PROFILE=lightly uv run python ../.experimental/ux-gap-prototype/bench_loaders.py \
        --limit 300 --db-rtt-ms 20
"""

from __future__ import annotations

import argparse
import json
import tempfile
import time
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import s3fs
from sqlalchemy import event

import lightly_studio as ls
from lightly_studio.database import db_manager

S3_ROOT = "s3://studio-test-datasets-eu/caltech_ux_run"
# The ux-iteration folder lives only in the main checkout, not in worktrees.
PREDICTIONS = Path(
    "~/dev/lightly/lightly-studio/.experimental/ux-iteration/train/model_v1_predictions.json"
).expanduser()

counts: Counter[str] = Counter()
statements: Counter[str] = Counter()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=300, help="Number of images to load.")
    parser.add_argument("--show-sql", action="store_true", help="Print top statements per step.")
    parser.add_argument("--predictions", type=Path, default=PREDICTIONS)
    parser.add_argument("--db-rtt-ms", type=float, default=0.0, help="Sleep per SQL statement.")
    args = parser.parse_args()

    work_dir = Path(tempfile.mkdtemp(prefix="bench_loaders_"))
    db_manager.connect(db_file=str(work_dir / "bench.db"), cleanup_existing=True)
    _instrument_db(rtt_s=args.db_rtt_ms / 1000)
    _instrument_s3()

    dataset = ls.ImageDataset.create(name="bench")
    with _step(name="add_samples_from_coco", images=args.limit, show_sql=args.show_sql):
        dataset.add_samples_from_coco(
            annotations_json=f"{S3_ROOT}/labels_noisy.json",
            images_path=f"{S3_ROOT}/images",
            embed=False,
            embed_annotations=False,
            limit=args.limit,
        )

    loaded_names = {sample.file_name for sample in dataset}
    predictions_json = _write_predictions_subset(
        predictions=args.predictions,
        file_names=loaded_names,
        output_path=work_dir / "predictions.json",
    )
    with _step(name="add_annotations_from_coco", images=len(loaded_names), show_sql=args.show_sql):
        dataset.add_annotations_from_coco(
            annotations_json=predictions_json,
            images_root=f"{S3_ROOT}/images",
            annotation_source="model_v1",
            embed_annotations=False,
        )


@contextmanager
def _step(name: str, images: int, show_sql: bool) -> Iterator[None]:
    counts.clear()
    statements.clear()
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start
    print(
        f"\n{name}: {images} images in {elapsed:.1f} s = {images / elapsed:.1f} images/s; "
        f"SQL statements: {counts['sql']}, S3 exists/info calls: {counts['s3']}"
    )
    if show_sql:
        for statement, count in statements.most_common(15):
            print(f"  {count:5d}  {statement}")


def _instrument_db(rtt_s: float) -> None:
    engine = db_manager.get_engine()._engine  # noqa: SLF001

    @event.listens_for(engine, "before_cursor_execute")
    def _count_and_delay(_conn: object, _cursor: object, statement: str, *_: object) -> None:
        counts["sql"] += 1
        statements[" ".join(statement.split())[:110]] += 1
        if rtt_s:
            time.sleep(rtt_s)


def _instrument_s3() -> None:
    for method_name in ("_exists", "_info"):
        original = getattr(s3fs.S3FileSystem, method_name)

        async def counted(self: object, *a: object, _original=original, **kw: object) -> object:  # type: ignore[no-untyped-def]
            counts["s3"] += 1
            return await _original(self, *a, **kw)

        setattr(s3fs.S3FileSystem, method_name, counted)


def _write_predictions_subset(predictions: Path, file_names: set[str], output_path: Path) -> Path:
    coco = json.loads(predictions.read_text())
    images = [image for image in coco["images"] if image["file_name"] in file_names]
    image_ids = {image["id"] for image in images}
    coco["images"] = images
    coco["annotations"] = [a for a in coco["annotations"] if a["image_id"] in image_ids]
    output_path.write_text(json.dumps(coco))
    return output_path


if __name__ == "__main__":
    main()
