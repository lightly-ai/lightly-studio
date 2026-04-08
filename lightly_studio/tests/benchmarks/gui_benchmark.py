"""Manual GUI benchmark dataset generator.

Run this script with `uv run tests/benchmarks/gui_benchmark.py` from the
`lightly_studio` directory, or from the repository root with
`uv run lightly_studio/tests/benchmarks/gui_benchmark.py`.
"""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID

import numpy as np
import pyarrow as pa
from numpy.typing import NDArray
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
    image_resolver,
)

DEFAULT_NUM_IMAGES = 100_000
DEFAULT_BOXES_PER_IMAGE = 10
DEFAULT_EMBEDDING_DIM = 512
DEFAULT_IMAGE_WIDTH = 1920
DEFAULT_IMAGE_HEIGHT = 1080
DEFAULT_IMAGE_FORMAT = "jpg"
DEFAULT_BATCH_SIZE = 5_000
DEFAULT_SEED = 0
DEFAULT_DATASET_NAME = "gui_benchmark"
DEFAULT_ANNOTATION_COLLECTION_NAME = "benchmark_annotations"
DEFAULT_ANNOTATION_LABEL_NAMES = ["car", "person", "bicycle", "truck", "bus"]
DEFAULT_EMBEDDING_MODEL_NAME = "benchmark_embeddings"


def _make_uuid_str(i: int) -> str:
    """Format an integer as a UUID string without creating a UUID object."""
    h = format(i, "032x")
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


@dataclass(frozen=True)
class BenchmarkConfig:
    """Configuration for generating the benchmark dataset."""

    num_images: int
    boxes_per_image: int
    embedding_dim: int
    image_width: int
    image_height: int
    image_format: str
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
        image_width=args.image_width,
        image_height=args.image_height,
        image_format=args.image_format,
        batch_size=args.batch_size,
        seed=args.seed,
        host=args.host,
        port=args.port,
    )
    _validate_config(config=config)

    with TemporaryDirectory(prefix="lightly_studio_gui_benchmark_") as tmp_dir:
        benchmark_dir = Path(tmp_dir)
        db_path = benchmark_dir / "benchmark.db"
        image_path = benchmark_dir / f"shared.{config.image_format}"

        setup_started = time.perf_counter()
        _create_shared_image(
            image_path=image_path,
            image_width=config.image_width,
            image_height=config.image_height,
        )
        _initialize_database(db_path=db_path)
        root_collection_id = _populate_database(config=config, image_path=image_path)
        _verify_annotation_counts(
            collection_id=root_collection_id,
            boxes_per_image=config.boxes_per_image,
        )

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
            start_gui_module.start_gui(host=preview_server.host, port=preview_server.port)
        finally:
            db_manager.close()


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--num-images", type=int, default=DEFAULT_NUM_IMAGES)
    parser.add_argument("--boxes-per-image", type=int, default=DEFAULT_BOXES_PER_IMAGE)
    parser.add_argument("--embedding-dim", type=int, default=DEFAULT_EMBEDDING_DIM)
    parser.add_argument("--image-width", type=int, default=DEFAULT_IMAGE_WIDTH)
    parser.add_argument("--image-height", type=int, default=DEFAULT_IMAGE_HEIGHT)
    parser.add_argument(
        "--image-format",
        type=str,
        default=DEFAULT_IMAGE_FORMAT,
        choices=["jpg", "jpeg", "png", "bmp", "webp", "tiff"],
    )
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
    if config.image_width <= 0:
        raise ValueError("--image-width must be greater than zero.")
    if config.image_height <= 0:
        raise ValueError("--image-height must be greater than zero.")
    if config.batch_size <= 0:
        raise ValueError("--batch-size must be greater than zero.")


def _create_shared_image(image_path: Path, image_width: int, image_height: int) -> None:
    """Create a single image file reused by every sample."""
    Image.new("RGB", (image_width, image_height), color=(120, 120, 120)).save(image_path)


def _initialize_database(db_path: Path) -> None:
    """Connect to a fresh on-disk DuckDB database."""
    db_manager.close()
    db_manager.connect(db_file=str(db_path), cleanup_existing=True)


def _populate_database(config: BenchmarkConfig, image_path: Path) -> UUID:
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
        annotation_label_ids = [
            annotation_label_resolver.create(
                session=session,
                label=AnnotationLabelCreate(
                    root_collection_id=root_collection.collection_id,
                    annotation_label_name=name,
                ),
            ).annotation_label_id
            for name in DEFAULT_ANNOTATION_LABEL_NAMES
        ]
        root_collection_id = root_collection.collection_id
        embedding_model_id = embedding_model.embedding_model_id

    _set_default_embedding_model(
        collection_id=root_collection_id,
        embedding_model_id=embedding_model_id,
    )
    raw_connection = db_manager.get_engine()._engine.raw_connection()
    try:
        connection = raw_connection.driver_connection
        with tqdm(
            total=config.num_images,
            desc="Populating database",
            unit="img",
        ) as progress:
            for batch_start in range(0, config.num_images, config.batch_size):
                batch_count = min(config.batch_size, config.num_images - batch_start)
                batch_data = _build_batch_data(
                    config=config,
                    batch_start=batch_start,
                    batch_count=batch_count,
                    rng=rng,
                    image_collection_id=root_collection_id,
                    annotation_collection_id=annotation_collection_id,
                    embedding_model_id=embedding_model_id,
                    annotation_label_ids=annotation_label_ids,
                    shared_image_path=image_path,
                )
                _insert_batch(connection=connection, batch_data=batch_data)
                progress.update(batch_count)
        raw_connection.commit()
    finally:
        raw_connection.close()
    return root_collection_id


def _verify_annotation_counts(collection_id: UUID, boxes_per_image: int) -> None:
    """Assert that every annotation label has at least one annotation."""
    if boxes_per_image == 0:
        return
    with db_manager.session() as session:
        counts = image_resolver.count_image_annotations_by_collection(
            session=session,
            collection_id=collection_id,
        )
    for label, current, total in counts:
        assert current > 0, f"Expected count > 0 for label '{label}', got {current}"
        assert total > 0, f"Expected total > 0 for label '{label}', got {total}"


def _set_default_embedding_model(collection_id: UUID, embedding_model_id: UUID) -> None:
    """Make the manually created embedding model visible to GUI embedding features."""
    embedding_manager = EmbeddingManagerProvider.get_embedding_manager()
    embedding_manager._collection_id_to_default_model_id[collection_id] = embedding_model_id


@dataclass(frozen=True)
class BatchData:
    """Arrow tables to insert for a single batch."""

    image_samples: pa.Table
    images: pa.Table
    embeddings: pa.Table
    annotation_samples: pa.Table
    annotations: pa.Table
    object_detections: pa.Table


@dataclass(frozen=True)
class ArrowInsertSpec:
    """Specification for inserting an Arrow table into a database table."""

    table_name: str
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
    annotation_label_ids: list[UUID],
    shared_image_path: Path,
) -> BatchData:
    """Build all Arrow tables for a batch."""
    image_id_strs = [_make_uuid_str(batch_start + i) for i in range(batch_count)]

    image_samples = _build_image_samples_table(
        image_id_strs=image_id_strs,
        collection_id_str=str(image_collection_id),
    )
    image_widths = rng.integers(
        int(config.image_width * 0.8),
        int(config.image_width * 1.2) + 1,
        size=batch_count,
        dtype=np.int32,
    )
    image_heights = rng.integers(
        int(config.image_height * 0.8),
        int(config.image_height * 1.2) + 1,
        size=batch_count,
        dtype=np.int32,
    )
    images = _build_images_table(
        batch_start=batch_start,
        image_id_strs=image_id_strs,
        shared_image_path=shared_image_path,
        image_format=config.image_format,
        widths=image_widths,
        heights=image_heights,
    )
    embeddings = _build_embeddings_table(
        rng=rng,
        image_id_strs=image_id_strs,
        embedding_dim=config.embedding_dim,
        embedding_model_id_str=str(embedding_model_id),
    )

    annotation_count = batch_count * config.boxes_per_image
    annotation_id_base = config.num_images + batch_start * config.boxes_per_image
    annotation_id_strs = [_make_uuid_str(annotation_id_base + i) for i in range(annotation_count)]

    annotation_samples = _build_annotation_samples_table(
        annotation_id_strs=annotation_id_strs,
        collection_id_str=str(annotation_collection_id),
    )
    annotations = _build_annotations_table(
        rng=rng,
        annotation_id_strs=annotation_id_strs,
        image_id_strs=image_id_strs,
        boxes_per_image=config.boxes_per_image,
        annotation_label_id_strs=[str(label_id) for label_id in annotation_label_ids],
    )
    object_detections = _build_object_detections_table(
        rng=rng,
        annotation_id_strs=annotation_id_strs,
        annotation_count=annotation_count,
        image_widths=image_widths,
        image_heights=image_heights,
        boxes_per_image=config.boxes_per_image,
    )

    return BatchData(
        image_samples=image_samples,
        images=images,
        embeddings=embeddings,
        annotation_samples=annotation_samples,
        annotations=annotations,
        object_detections=object_detections,
    )


def _build_image_samples_table(
    image_id_strs: list[str],
    collection_id_str: str,
) -> pa.Table:
    """Build the image samples Arrow table."""
    n = len(image_id_strs)
    return pa.table(
        {
            "sample_id": pa.array(image_id_strs, type=pa.string()),
            "collection_id": pa.array([collection_id_str] * n, type=pa.string()),
        }
    )


def _build_images_table(  # noqa: PLR0913
    batch_start: int,
    image_id_strs: list[str],
    shared_image_path: Path,
    image_format: str,
    widths: NDArray[np.int32],
    heights: NDArray[np.int32],
) -> pa.Table:
    """Build the images Arrow table."""
    n = len(image_id_strs)
    file_path_str = str(shared_image_path)
    file_names = [f"benchmark_{batch_start + i:06d}.{image_format}" for i in range(n)]
    return pa.table(
        {
            "sample_id": pa.array(image_id_strs, type=pa.string()),
            "file_name": pa.array(file_names, type=pa.string()),
            "file_path_abs": pa.array([file_path_str] * n, type=pa.string()),
            "width": pa.array(widths, type=pa.int32()),
            "height": pa.array(heights, type=pa.int32()),
        }
    )


def _build_embeddings_table(
    rng: np.random.Generator,
    image_id_strs: list[str],
    embedding_dim: int,
    embedding_model_id_str: str,
) -> pa.Table:
    """Build the embeddings Arrow table using a FixedSizeListArray."""
    n = len(image_id_strs)
    flat = rng.random(n * embedding_dim, dtype=np.float32)
    embedding_array = pa.FixedSizeListArray.from_arrays(
        pa.array(flat, type=pa.float32()),
        embedding_dim,
    )
    return pa.table(
        {
            "sample_id": pa.array(image_id_strs, type=pa.string()),
            "embedding_model_id": pa.array([embedding_model_id_str] * n, type=pa.string()),
            "embedding": embedding_array,
        }
    )


def _build_annotation_samples_table(
    annotation_id_strs: list[str],
    collection_id_str: str,
) -> pa.Table:
    """Build the annotation samples Arrow table."""
    n = len(annotation_id_strs)
    return pa.table(
        {
            "sample_id": pa.array(annotation_id_strs, type=pa.string()),
            "collection_id": pa.array([collection_id_str] * n, type=pa.string()),
        }
    )


def _build_annotations_table(
    rng: np.random.Generator,
    annotation_id_strs: list[str],
    image_id_strs: list[str],
    boxes_per_image: int,
    annotation_label_id_strs: list[str],
) -> pa.Table:
    """Build the annotations Arrow table with randomly assigned labels."""
    n = len(annotation_id_strs)
    repeated_parent_ids = np.repeat(np.array(image_id_strs), boxes_per_image)
    label_choices = np.array(annotation_label_id_strs)
    chosen_labels = label_choices[rng.integers(0, len(label_choices), size=n)]
    return pa.table(
        {
            "sample_id": pa.array(annotation_id_strs, type=pa.string()),
            "annotation_type": pa.array(
                [AnnotationType.OBJECT_DETECTION.value.upper()] * n, type=pa.string()
            ),
            "annotation_label_id": pa.array(chosen_labels, type=pa.string()),
            "parent_sample_id": pa.array(repeated_parent_ids, type=pa.string()),
        }
    )


def _build_object_detections_table(  # noqa: PLR0913
    rng: np.random.Generator,
    annotation_id_strs: list[str],
    annotation_count: int,
    image_widths: NDArray[np.int32],
    image_heights: NDArray[np.int32],
    boxes_per_image: int,
) -> pa.Table:
    """Build the object detections Arrow table."""
    if annotation_count == 0:
        return pa.table(
            {
                "sample_id": pa.array([], type=pa.string()),
                "x": pa.array([], type=pa.int32()),
                "y": pa.array([], type=pa.int32()),
                "width": pa.array([], type=pa.int32()),
                "height": pa.array([], type=pa.int32()),
            }
        )
    parent_widths = np.repeat(image_widths, boxes_per_image).astype(np.int32)
    parent_heights = np.repeat(image_heights, boxes_per_image).astype(np.int32)
    max_w = np.maximum(2, parent_widths // 4)
    max_h = np.maximum(2, parent_heights // 4)
    widths = np.minimum(
        rng.integers(1, int(max_w.max()) + 1, size=annotation_count, dtype=np.int32),
        parent_widths,
    )
    heights = np.minimum(
        rng.integers(1, int(max_h.max()) + 1, size=annotation_count, dtype=np.int32),
        parent_heights,
    )
    x_values = (rng.random(annotation_count) * (parent_widths - widths + 1)).astype(np.int32)
    y_values = (rng.random(annotation_count) * (parent_heights - heights + 1)).astype(np.int32)
    return pa.table(
        {
            "sample_id": pa.array(annotation_id_strs, type=pa.string()),
            "x": pa.array(x_values, type=pa.int32()),
            "y": pa.array(y_values, type=pa.int32()),
            "width": pa.array(widths, type=pa.int32()),
            "height": pa.array(heights, type=pa.int32()),
        }
    )


def _insert_batch(connection: object, batch_data: BatchData) -> None:
    """Insert a single batch into the database."""
    _insert_arrow_table(
        connection=connection,
        table=batch_data.image_samples,
        spec=ArrowInsertSpec(
            table_name=SampleTable.__tablename__,
            insert_columns=("sample_id", "collection_id", "created_at", "updated_at"),
            select_columns_sql="sample_id, collection_id, current_timestamp, current_timestamp",
        ),
    )
    _insert_arrow_table(
        connection=connection,
        table=batch_data.images,
        spec=ArrowInsertSpec(
            table_name=ImageTable.__tablename__,
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
    _insert_arrow_table(
        connection=connection,
        table=batch_data.embeddings,
        spec=ArrowInsertSpec(
            table_name=SampleEmbeddingTable.__tablename__,
        ),
    )

    if len(batch_data.annotation_samples) > 0:
        _insert_arrow_table(
            connection=connection,
            table=batch_data.annotation_samples,
            spec=ArrowInsertSpec(
                table_name=SampleTable.__tablename__,
                insert_columns=("sample_id", "collection_id", "created_at", "updated_at"),
                select_columns_sql="sample_id, collection_id, current_timestamp, current_timestamp",
            ),
        )
        _insert_arrow_table(
            connection=connection,
            table=batch_data.annotations,
            spec=ArrowInsertSpec(
                table_name=AnnotationBaseTable.__tablename__,
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
        _insert_arrow_table(
            connection=connection,
            table=batch_data.object_detections,
            spec=ArrowInsertSpec(
                table_name=ObjectDetectionAnnotationTable.__tablename__,
            ),
        )


def _insert_arrow_table(
    connection: object,
    table: pa.Table,
    spec: ArrowInsertSpec,
) -> None:
    """Register an Arrow table in DuckDB and INSERT it into the target table."""
    if len(table) == 0:
        return

    source_cols = table.column_names
    insert_cols = spec.insert_columns or tuple(source_cols)
    select_sql = spec.select_columns_sql or ", ".join(source_cols)
    column_list = ", ".join(insert_cols)

    temp_name = f"tmp_{spec.table_name}"
    connection.register(temp_name, table)  # type: ignore[attr-defined]
    try:
        connection.cursor().execute(  # type: ignore[attr-defined]
            f"INSERT INTO {spec.table_name} ({column_list}) SELECT {select_sql} FROM {temp_name}"
        )
    finally:
        connection.unregister(temp_name)  # type: ignore[attr-defined]


if __name__ == "__main__":
    main()
