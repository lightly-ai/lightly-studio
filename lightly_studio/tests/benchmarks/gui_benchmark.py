"""Manual GUI benchmark dataset generator.

Run this script with `uv run tests/benchmarks/gui_benchmark.py` from the
`lightly_studio` directory, or from the repository root with
`uv run lightly_studio/tests/benchmarks/gui_benchmark.py`.
"""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID, uuid4

import numpy as np
import pyarrow as pa
from PIL import Image
from tqdm import tqdm

import lightly_studio.core.start_gui as start_gui_module
from lightly_studio import db_manager
from lightly_studio.api.server import Server
from lightly_studio.dataset.embedding_manager import EmbeddingManagerProvider
from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationType,
)
from lightly_studio.models.annotation.object_detection import (
    ObjectDetectionAnnotationTable,
)
from lightly_studio.models.annotation_label import AnnotationLabelCreate
from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.models.embedding_model import EmbeddingModelCreate
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.resolvers import (
    annotation_label_resolver,
    collection_resolver,
    embedding_model_resolver,
)

DEFAULT_NUM_IMAGES = 100_000
DEFAULT_BOXES_PER_IMAGE = 10
DEFAULT_EMBEDDING_DIM = 512
DEFAULT_IMAGE_SIZE = 640
DEFAULT_BATCH_SIZE = 2_000
DEFAULT_SEED = 0
DEFAULT_DATASET_NAME = "gui_benchmark"
DEFAULT_ANNOTATION_COLLECTION_NAME = "benchmark_annotations"
DEFAULT_ANNOTATION_LABEL_NAME = "object"
DEFAULT_EMBEDDING_MODEL_NAME = "benchmark_embeddings"
Row = dict[str, object]


@dataclass(frozen=True)
class BenchmarkConfig:
    """Configuration for generating the benchmark dataset."""

    num_images: int
    boxes_per_image: int
    embedding_dim: int
    image_size: int
    batch_size: int
    seed: int
    host: str | None
    port: int | None


def main() -> None:
    """Create the benchmark dataset and start the GUI."""
    args = _parse_args()
    config = BenchmarkConfig(
        num_images=args.num_images,
        boxes_per_image=args.boxes_per_image,
        embedding_dim=args.embedding_dim,
        image_size=args.image_size,
        batch_size=args.batch_size,
        seed=args.seed,
        host=args.host,
        port=args.port,
    )
    _validate_config(config=config)

    with TemporaryDirectory(prefix="lightly_studio_gui_benchmark_") as tmp_dir:
        benchmark_dir = Path(tmp_dir)
        db_path = benchmark_dir / "benchmark.db"
        image_path = benchmark_dir / "shared.jpg"

        setup_started = time.perf_counter()
        _create_shared_image(image_path=image_path, image_size=config.image_size)
        _initialize_database(db_path=db_path)
        _populate_database(config=config, image_path=image_path)

        preview_server = Server(host=config.host, port=config.port)
        setup_elapsed = time.perf_counter() - setup_started
        print(
            "Benchmark ready: "
            f"setup_time={setup_elapsed:.3f}s "
            f"db={db_path} "
            f"url={preview_server.url}",
            flush=True,
        )

        try:
            start_gui_module.start_gui(host=config.host, port=config.port)
        finally:
            db_manager.close()


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--num-images", type=int, default=DEFAULT_NUM_IMAGES)
    parser.add_argument("--boxes-per-image", type=int, default=DEFAULT_BOXES_PER_IMAGE)
    parser.add_argument("--embedding-dim", type=int, default=DEFAULT_EMBEDDING_DIM)
    parser.add_argument("--image-size", type=int, default=DEFAULT_IMAGE_SIZE)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--host", type=str, default=None)
    parser.add_argument("--port", type=int, default=None)
    return parser.parse_args()


def _validate_config(config: BenchmarkConfig) -> None:
    """Validate the benchmark configuration."""
    if config.num_images <= 0:
        raise ValueError("--num-images must be greater than zero.")
    if config.boxes_per_image < 0:
        raise ValueError("--boxes-per-image must be zero or greater.")
    if config.embedding_dim <= 0:
        raise ValueError("--embedding-dim must be greater than zero.")
    if config.image_size <= 0:
        raise ValueError("--image-size must be greater than zero.")
    if config.batch_size <= 0:
        raise ValueError("--batch-size must be greater than zero.")


def _create_shared_image(image_path: Path, image_size: int) -> None:
    """Create a single image file reused by every sample."""
    Image.new("RGB", (image_size, image_size), color=(120, 120, 120)).save(image_path)


def _initialize_database(db_path: Path) -> None:
    """Connect to a fresh on-disk DuckDB database."""
    db_manager.close()
    db_manager.connect(db_file=str(db_path), cleanup_existing=True)


def _populate_database(config: BenchmarkConfig, image_path: Path) -> None:
    """Populate the benchmark dataset with images, embeddings, and annotations."""
    rng = np.random.default_rng(config.seed)
    with db_manager.session() as session:
        root_collection = collection_resolver.create(
            session=session,
            collection=CollectionCreate(
                name=DEFAULT_DATASET_NAME,
                sample_type=SampleType.IMAGE,
            ),
        )
        annotation_collection_id = collection_resolver.get_or_create_child_collection(
            session=session,
            collection_id=root_collection.collection_id,
            sample_type=SampleType.ANNOTATION,
            name=DEFAULT_ANNOTATION_COLLECTION_NAME,
        )
        embedding_model = embedding_model_resolver.create(
            session=session,
            embedding_model=EmbeddingModelCreate(
                collection_id=root_collection.collection_id,
                name=DEFAULT_EMBEDDING_MODEL_NAME,
                embedding_dimension=config.embedding_dim,
            ),
        )
        annotation_label = annotation_label_resolver.create(
            session=session,
            label=AnnotationLabelCreate(
                root_collection_id=root_collection.collection_id,
                annotation_label_name=DEFAULT_ANNOTATION_LABEL_NAME,
            ),
        )
        root_collection_id = root_collection.collection_id
        annotation_label_id = annotation_label.annotation_label_id
        embedding_model_id = embedding_model.embedding_model_id

    _set_default_embedding_model(
        collection_id=root_collection_id,
        embedding_model_id=embedding_model_id,
    )
    raw_connection = db_manager.get_engine()._engine.raw_connection()
    try:
        connection = raw_connection.driver_connection
        for batch_start in tqdm(
            range(0, config.num_images, config.batch_size),
            desc="Populating database",
        ):
            batch_count = min(config.batch_size, config.num_images - batch_start)
            batch_data = _build_batch_data(
                config=config,
                batch_start=batch_start,
                batch_count=batch_count,
                rng=rng,
                image_collection_id=root_collection_id,
                annotation_collection_id=annotation_collection_id,
                embedding_model_id=embedding_model_id,
                annotation_label_id=annotation_label_id,
                shared_image_path=image_path,
            )
            _insert_batch(connection=connection, batch_data=batch_data)
        raw_connection.commit()
    finally:
        raw_connection.close()


def _set_default_embedding_model(collection_id: UUID, embedding_model_id: UUID) -> None:
    """Make the manually created embedding model visible to GUI embedding features."""
    embedding_manager = EmbeddingManagerProvider.get_embedding_manager()
    embedding_manager._collection_id_to_default_model_id[collection_id] = embedding_model_id


@dataclass(frozen=True)
class BatchData:
    """Rows to insert for a single batch."""

    image_samples: list[Row]
    images: list[Row]
    embeddings: list[Row]
    annotation_samples: list[Row]
    annotations: list[Row]
    object_detections: list[Row]


@dataclass(frozen=True)
class ArrowInsertSpec:
    """Specification for inserting Arrow-backed rows into a table."""

    table_name: str
    source_columns: tuple[str, ...]
    insert_columns: tuple[str, ...] | None = None
    select_columns_sql: str | None = None


def _build_batch_data(  # noqa: PLR0913
    config: BenchmarkConfig,
    batch_start: int,
    batch_count: int,
    rng: np.random.Generator,
    image_collection_id: UUID,
    annotation_collection_id: UUID,
    embedding_model_id: UUID,
    annotation_label_id: UUID,
    shared_image_path: Path,
) -> BatchData:
    """Build all row payloads for a batch."""
    image_sample_ids = [uuid4() for _ in range(batch_count)]
    image_samples: list[Row] = [
        {"sample_id": sample_id, "collection_id": image_collection_id}
        for sample_id in image_sample_ids
    ]
    images = _build_image_rows(
        batch_start=batch_start,
        image_size=config.image_size,
        image_sample_ids=image_sample_ids,
        shared_image_path=shared_image_path,
    )
    embeddings = _build_embedding_rows(
        rng=rng,
        embedding_dim=config.embedding_dim,
        embedding_model_id=embedding_model_id,
        image_sample_ids=image_sample_ids,
    )

    annotation_count = batch_count * config.boxes_per_image
    annotation_sample_ids = [uuid4() for _ in range(annotation_count)]
    annotation_samples: list[Row] = [
        {"sample_id": sample_id, "collection_id": annotation_collection_id}
        for sample_id in annotation_sample_ids
    ]
    annotations, object_detections = _build_annotation_rows(
        rng=rng,
        image_size=config.image_size,
        boxes_per_image=config.boxes_per_image,
        annotation_label_id=annotation_label_id,
        annotation_sample_ids=annotation_sample_ids,
        image_sample_ids=image_sample_ids,
    )

    return BatchData(
        image_samples=image_samples,
        images=images,
        embeddings=embeddings,
        annotation_samples=annotation_samples,
        annotations=annotations,
        object_detections=object_detections,
    )


def _build_image_rows(
    batch_start: int,
    image_size: int,
    image_sample_ids: list[UUID],
    shared_image_path: Path,
) -> list[Row]:
    """Build image rows for a batch."""
    rows: list[Row] = []
    shared_image_path_str = str(shared_image_path)
    for index, sample_id in enumerate(image_sample_ids, start=batch_start):
        rows.append(
            {
                "sample_id": sample_id,
                "file_name": f"benchmark_{index:06d}.jpg",
                "file_path_abs": shared_image_path_str,
                "width": image_size,
                "height": image_size,
            }
        )
    return rows


def _build_embedding_rows(
    rng: np.random.Generator,
    embedding_dim: int,
    embedding_model_id: UUID,
    image_sample_ids: list[UUID],
) -> list[Row]:
    """Build embedding rows for a batch."""
    embeddings = rng.random((len(image_sample_ids), embedding_dim))
    return [
        {
            "sample_id": sample_id,
            "embedding_model_id": embedding_model_id,
            "embedding": embedding.tolist(),
        }
        for sample_id, embedding in zip(image_sample_ids, embeddings)
    ]


def _build_annotation_rows(  # noqa: PLR0913
    rng: np.random.Generator,
    image_size: int,
    boxes_per_image: int,
    annotation_label_id: UUID,
    annotation_sample_ids: list[UUID],
    image_sample_ids: list[UUID],
) -> tuple[list[Row], list[Row]]:
    """Build annotation rows for a batch."""
    if boxes_per_image == 0:
        return [], []

    repeated_parent_ids = [
        sample_id for sample_id in image_sample_ids for _ in range(boxes_per_image)
    ]
    box_count = len(annotation_sample_ids)
    max_box_size = max(2, image_size // 4)
    widths = rng.integers(1, max_box_size + 1, size=box_count, dtype=np.int32)
    heights = rng.integers(1, max_box_size + 1, size=box_count, dtype=np.int32)
    x_values = rng.integers(0, image_size - widths + 1, size=box_count, dtype=np.int32)
    y_values = rng.integers(0, image_size - heights + 1, size=box_count, dtype=np.int32)

    annotations: list[Row] = []
    object_detections: list[Row] = []
    for index, annotation_sample_id in enumerate(annotation_sample_ids):
        annotations.append(
            {
                "sample_id": annotation_sample_id,
                "annotation_type": AnnotationType.OBJECT_DETECTION,
                "annotation_label_id": annotation_label_id,
                "parent_sample_id": repeated_parent_ids[index],
            }
        )
        object_detections.append(
            {
                "sample_id": annotation_sample_id,
                "x": int(x_values[index]),
                "y": int(y_values[index]),
                "width": int(widths[index]),
                "height": int(heights[index]),
            }
        )
    return annotations, object_detections


def _insert_batch(connection: object, batch_data: BatchData) -> None:
    """Insert a single batch into the database."""
    _insert_arrow_rows(
        connection=connection,
        rows=batch_data.image_samples,
        spec=ArrowInsertSpec(
            table_name=SampleTable.__tablename__,
            source_columns=("sample_id", "collection_id"),
            insert_columns=("sample_id", "collection_id", "created_at", "updated_at"),
            select_columns_sql="sample_id, collection_id, current_timestamp, current_timestamp",
        ),
    )
    _insert_arrow_rows(
        connection=connection,
        rows=batch_data.images,
        spec=ArrowInsertSpec(
            table_name=ImageTable.__tablename__,
            source_columns=("sample_id", "file_name", "width", "height", "file_path_abs"),
            insert_columns=(
                "sample_id",
                "file_name",
                "width",
                "height",
                "file_path_abs",
                "created_at",
                "updated_at",
            ),
            select_columns_sql=(
                "sample_id, file_name, width, height, file_path_abs, "
                "current_timestamp, current_timestamp"
            ),
        ),
    )
    _insert_arrow_rows(
        connection=connection,
        rows=batch_data.embeddings,
        spec=ArrowInsertSpec(
            table_name=SampleEmbeddingTable.__tablename__,
            source_columns=("sample_id", "embedding_model_id", "embedding"),
        ),
    )

    if batch_data.annotation_samples:
        _insert_arrow_rows(
            connection=connection,
            rows=batch_data.annotation_samples,
            spec=ArrowInsertSpec(
                table_name=SampleTable.__tablename__,
                source_columns=("sample_id", "collection_id"),
                insert_columns=("sample_id", "collection_id", "created_at", "updated_at"),
                select_columns_sql="sample_id, collection_id, current_timestamp, current_timestamp",
            ),
        )
        _insert_arrow_rows(
            connection=connection,
            rows=batch_data.annotations,
            spec=ArrowInsertSpec(
                table_name=AnnotationBaseTable.__tablename__,
                source_columns=(
                    "sample_id",
                    "annotation_type",
                    "annotation_label_id",
                    "parent_sample_id",
                ),
                insert_columns=(
                    "sample_id",
                    "annotation_type",
                    "annotation_label_id",
                    "parent_sample_id",
                    "created_at",
                ),
                select_columns_sql=(
                    "sample_id, annotation_type, annotation_label_id, parent_sample_id, "
                    "current_timestamp"
                ),
            ),
        )
        _insert_arrow_rows(
            connection=connection,
            rows=batch_data.object_detections,
            spec=ArrowInsertSpec(
                table_name=ObjectDetectionAnnotationTable.__tablename__,
                source_columns=("sample_id", "x", "y", "width", "height"),
            ),
        )


def _insert_arrow_rows(
    connection: object,
    rows: list[Row],
    spec: ArrowInsertSpec,
) -> None:
    """Insert rows into DuckDB through an Arrow table."""
    if not rows:
        return

    arrow_table = pa.table(
        {
            column: [_normalize_arrow_value(row[column]) for row in rows]
            for column in spec.source_columns
        }
    )
    temp_table_name = f"tmp_{spec.table_name}_{uuid4().hex}"
    connection.register(temp_table_name, arrow_table)  # type: ignore[attr-defined]

    column_list = ", ".join(spec.insert_columns or spec.source_columns)
    select_list = spec.select_columns_sql or ", ".join(spec.source_columns)
    try:
        cursor = connection.cursor()  # type: ignore[attr-defined]
        cursor.execute(
            f"INSERT INTO {spec.table_name} ({column_list}) "
            f"SELECT {select_list} FROM {temp_table_name}"
        )
    finally:
        connection.unregister(temp_table_name)  # type: ignore[attr-defined]


def _normalize_arrow_value(value: object) -> object:
    """Convert Python objects into Arrow-friendly scalar values."""
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Enum):
        return value.name
    return value


if __name__ == "__main__":
    main()
