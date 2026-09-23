"""Object-detection evaluation benchmark.

Measures ``dataset.evaluate().object_detection(...)`` on a synthetic dataset and
reports the wall-clock time and the number of SELECT statements, on either a
temporary DuckDB file (default) or PostgreSQL (``--postgres``).

Evaluation matches every sample first and then stores the metrics. If a metric
commit happens before a sample is matched, the commit expires the loaded
annotations and each one is loaded again with its own SELECT. The SELECT count
shows if this happens.

Run from the ``lightly_studio`` directory:

    uv run tests/benchmarks/evaluation_benchmark.py

Against PostgreSQL:

    make start-postgres
    uv run tests/benchmarks/evaluation_benchmark.py --postgres
    make stop-postgres
"""

from __future__ import annotations

import argparse
import os
import random
import time
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from uuid import UUID

import sqlalchemy

from lightly_studio.core.image.image_dataset import ImageDataset
from lightly_studio.database import db_manager
from lightly_studio.evaluation.image_dataset_evaluate import ObjectDetectionEvaluationConfig
from lightly_studio.models.annotation.annotation_base import AnnotationCreate, AnnotationType
from lightly_studio.models.annotation_label import AnnotationLabelCreate
from lightly_studio.models.image import ImageCreate
from lightly_studio.resolvers import (
    annotation_label_resolver,
    annotation_resolver,
    image_resolver,
)

DEFAULT_NUM_IMAGES = 10_000
DEFAULT_NUM_CLASSES = 20
DEFAULT_GT_PER_IMAGE = 8
DEFAULT_FALSE_POSITIVES_PER_IMAGE = 3
DEFAULT_BATCH_SIZE = 5_000
DEFAULT_DATASET_NAME = "evaluation_benchmark"
DEFAULT_POSTGRES_URL = "postgresql://lightly:lightly@localhost:5433/lightly_studio"

_IMAGE_SIZE = 1_000
_GT_SOURCE = "gt"
_PRED_SOURCE = "pred"


@dataclass(frozen=True)
class BenchmarkConfig:
    """Configuration for the evaluation benchmark."""

    num_images: int
    num_classes: int
    gt_per_image: int
    false_positives_per_image: int
    batch_size: int
    seed: int
    postgres: bool


def main() -> None:
    """Run the evaluation benchmark and print a report."""
    args = _parse_args()
    config = BenchmarkConfig(
        num_images=args.num_images,
        num_classes=args.num_classes,
        gt_per_image=args.gt_per_image,
        false_positives_per_image=args.false_positives_per_image,
        batch_size=args.batch_size,
        seed=args.seed,
        postgres=args.postgres,
    )
    _validate_config(config=config)

    with TemporaryDirectory(prefix="lightly_studio_evaluation_benchmark_") as tmp_dir:
        db_path = Path(tmp_dir) / "benchmark.db"
        db_target = _connect_database(db_path=db_path, use_postgres=config.postgres)

        try:
            dataset, annotation_count = _setup(config=config)
            wall_seconds, select_count = _run_evaluation(dataset=dataset)
        finally:
            db_manager.close()

    _print_report(
        config=config,
        db_target=db_target,
        annotation_count=annotation_count,
        wall_seconds=wall_seconds,
        select_count=select_count,
    )


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--num-images", type=int, default=DEFAULT_NUM_IMAGES)
    parser.add_argument("--num-classes", type=int, default=DEFAULT_NUM_CLASSES)
    parser.add_argument("--gt-per-image", type=int, default=DEFAULT_GT_PER_IMAGE)
    parser.add_argument(
        "--false-positives-per-image", type=int, default=DEFAULT_FALSE_POSITIVES_PER_IMAGE
    )
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--postgres",
        action="store_true",
        help=(
            "Benchmark against PostgreSQL instead of a temporary DuckDB file. "
            "Uses $LIGHTLY_STUDIO_DATABASE_URL if set, otherwise "
            f"{DEFAULT_POSTGRES_URL}."
        ),
    )
    return parser.parse_args()


def _validate_config(config: BenchmarkConfig) -> None:
    """Validate the benchmark configuration."""
    if config.num_images <= 0:
        raise ValueError("--num-images must be greater than zero.")
    if config.num_classes <= 0:
        raise ValueError("--num-classes must be greater than zero.")
    if config.gt_per_image <= 0:
        raise ValueError("--gt-per-image must be greater than zero.")
    if config.false_positives_per_image < 0:
        raise ValueError("--false-positives-per-image must not be negative.")
    if config.batch_size <= 0:
        raise ValueError("--batch-size must be greater than zero.")


def _connect_database(db_path: Path, use_postgres: bool) -> str:
    """Connect to a fresh database and return a description of its target."""
    db_manager.close()
    if use_postgres:
        database_url = os.environ.get("LIGHTLY_STUDIO_DATABASE_URL", DEFAULT_POSTGRES_URL)
        db_manager.connect(db_url=database_url, cleanup_existing=True)
        return database_url
    db_manager.connect(db_file=str(db_path), cleanup_existing=True)
    return str(db_path)


def _setup(config: BenchmarkConfig) -> tuple[ImageDataset, int]:
    """Create a dataset with ground-truth and prediction boxes.

    Each ground-truth box has a matching prediction with probability 0.8. The
    prediction is shifted by a few pixels and has the wrong label with probability
    0.1. Each image also gets random false-positive predictions with low confidence.

    Returns the dataset and the number of created annotations.
    """
    rng = random.Random(config.seed)
    dataset = ImageDataset.create(name=DEFAULT_DATASET_NAME)
    session = dataset.session
    label_ids = [
        annotation_label_resolver.create(
            session=session,
            label=AnnotationLabelCreate(
                dataset_id=dataset.dataset_id,
                annotation_label_name=f"class_{index:02d}",
            ),
        ).annotation_label_id
        for index in range(config.num_classes)
    ]

    annotation_count = 0
    for start in range(0, config.num_images, config.batch_size):
        stop = min(start + config.batch_size, config.num_images)
        sample_ids = image_resolver.create_many(
            session=session,
            collection_id=dataset.collection_id,
            samples=[
                ImageCreate(
                    file_name=f"image_{index:07d}.jpg",
                    file_path_abs=f"/benchmark/image_{index:07d}.jpg",
                    width=_IMAGE_SIZE,
                    height=_IMAGE_SIZE,
                )
                for index in range(start, stop)
            ],
        )
        gt_annotations: list[AnnotationCreate] = []
        pred_annotations: list[AnnotationCreate] = []
        for sample_id in sample_ids:
            for _ in range(config.gt_per_image):
                label_id = rng.choice(label_ids)
                box = _random_box(rng=rng)
                gt_annotations.append(_box(sample_id=sample_id, label_id=label_id, box=box))
                if rng.random() < 0.8:
                    pred_label_id = label_id if rng.random() < 0.9 else rng.choice(label_ids)
                    pred_annotations.append(
                        _box(
                            sample_id=sample_id,
                            label_id=pred_label_id,
                            box=_jitter(rng=rng, box=box),
                            confidence=rng.uniform(0.3, 1.0),
                        )
                    )
            for _ in range(config.false_positives_per_image):
                pred_annotations.append(
                    _box(
                        sample_id=sample_id,
                        label_id=rng.choice(label_ids),
                        box=_random_box(rng=rng),
                        confidence=rng.uniform(0.0, 0.6),
                    )
                )
        for source, source_annotations in (
            (_GT_SOURCE, gt_annotations),
            (_PRED_SOURCE, pred_annotations),
        ):
            annotation_resolver.create_many(
                session=session,
                parent_collection_id=dataset.collection_id,
                annotations=source_annotations,
                collection_name=source,
            )
            annotation_count += len(source_annotations)
        session.commit()
    return dataset, annotation_count


def _run_evaluation(dataset: ImageDataset) -> tuple[float, int]:
    """Run the evaluation and return its wall-clock time and SELECT count."""
    select_count = 0

    def count_selects(*args: Any) -> None:
        nonlocal select_count
        # The statement is the third argument of the before_cursor_execute event.
        if args[2].lstrip().upper().startswith("SELECT"):
            select_count += 1

    engine = dataset.session.get_bind()
    sqlalchemy.event.listen(engine, "before_cursor_execute", count_selects)
    try:
        started = time.perf_counter()
        dataset.evaluate().object_detection(
            name="benchmark",
            gt_annotation_source=_GT_SOURCE,
            pred_annotation_source=_PRED_SOURCE,
            config=ObjectDetectionEvaluationConfig(),
        )
        wall_seconds = time.perf_counter() - started
    finally:
        sqlalchemy.event.remove(engine, "before_cursor_execute", count_selects)
    return wall_seconds, select_count


def _print_report(
    config: BenchmarkConfig,
    db_target: str,
    annotation_count: int,
    wall_seconds: float,
    select_count: int,
) -> None:
    """Print a compact, copy-pasteable results block."""
    backend = "postgres" if config.postgres else "duckdb"
    print("")
    print("Evaluation benchmark")
    print(
        f"  backend={backend} db={db_target} num_images={config.num_images} "
        f"annotations={annotation_count}"
    )
    print(
        f"  object_detection time={wall_seconds:8.3f}s "
        f"throughput={config.num_images / wall_seconds:8.1f} images/s "
        f"selects={select_count}"
    )


def _random_box(rng: random.Random) -> tuple[int, int, int, int]:
    """Return a random ``(x, y, width, height)`` box inside the image."""
    width = rng.randint(20, 200)
    height = rng.randint(20, 200)
    return rng.randint(0, _IMAGE_SIZE - width), rng.randint(0, _IMAGE_SIZE - height), width, height


def _jitter(rng: random.Random, box: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    """Return the box shifted and resized by a few pixels."""
    x, y, width, height = box
    return (
        max(0, x + rng.randint(-8, 8)),
        max(0, y + rng.randint(-8, 8)),
        max(1, width + rng.randint(-8, 8)),
        max(1, height + rng.randint(-8, 8)),
    )


def _box(
    sample_id: UUID,
    label_id: UUID,
    box: tuple[int, int, int, int],
    confidence: float | None = None,
) -> AnnotationCreate:
    """Return an object-detection annotation for the image."""
    x, y, width, height = box
    return AnnotationCreate(
        annotation_label_id=label_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
        confidence=confidence,
        parent_sample_id=sample_id,
        x=x,
        y=y,
        width=width,
        height=height,
    )


if __name__ == "__main__":
    main()
