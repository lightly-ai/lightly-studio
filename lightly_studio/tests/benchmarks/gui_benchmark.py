"""Manual GUI benchmark dataset generator.

Run this script with `uv run tests/benchmarks/gui_benchmark.py` from the
`lightly_studio` directory, or from the repository root with
`uv run lightly_studio/tests/benchmarks/gui_benchmark.py`.

The target database is selected with `--backend`:

DuckDB (default):

    uv run tests/benchmarks/gui_benchmark.py

Local PostgreSQL:

    make start-postgres
    uv run tests/benchmarks/gui_benchmark.py --backend postgres
    make stop-postgres

Remote enterprise instance (credentials come from the environment):

    export LIGHTLY_STUDIO_API_URL="http://<enterprise-host>:8400"
    export LIGHTLY_STUDIO_TOKEN="<token-from-the-enterprise-GUI>"
    uv run tests/benchmarks/gui_benchmark.py --backend enterprise

The enterprise backend does not wipe the remote database, so it creates a uniquely
named dataset per run and leaves the data in place for inspection.
"""

from __future__ import annotations

import argparse
import logging
import os
import secrets
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from uuid import UUID

import numpy as np
import pgvector.psycopg
import pyarrow as pa
from numpy.typing import NDArray
from PIL import Image
from sqlmodel import Session
from tqdm import tqdm

import lightly_studio.core.start_gui as start_gui_module
from lightly_studio import enterprise
from lightly_studio.api.server import Server
from lightly_studio.database import db_manager
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
DEFAULT_POSTGRES_URL = "postgresql://lightly:lightly@localhost:5433/lightly_studio"

logger = logging.getLogger(__name__)


def _make_uuid_str(i: int) -> str:
    """Format an integer as a UUID string without creating a UUID object."""
    h = format(i, "032x")
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


class Backend(str, Enum):
    """Database backend the benchmark runs against."""

    DUCKDB = "duckdb"
    POSTGRES = "postgres"
    ENTERPRISE = "enterprise"


@dataclass(frozen=True)
class BenchmarkConfig:
    """Configuration for generating the benchmark dataset."""

    num_images: int
    boxes_per_image: int
    image_width: int
    image_height: int
    image_format: str
    batch_size: int
    seed: int
    host: str | None
    port: int | None
    backend: Backend
    id_offset: int


def main() -> None:
    """Create the benchmark dataset and start the GUI."""
    args = _parse_args()
    config = BenchmarkConfig(
        num_images=args.num_images,
        boxes_per_image=args.boxes_per_image,
        image_width=args.image_width,
        image_height=args.image_height,
        image_format=args.image_format,
        batch_size=args.batch_size,
        seed=args.seed,
        host=args.host,
        port=args.port,
        backend=Backend(args.backend),
        id_offset=_resolve_id_offset(backend=Backend(args.backend)),
    )
    _validate_config(config=config)

    dataset_name = _resolve_dataset_name(backend=config.backend)

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
        db_target = _initialize_database(db_path=db_path, backend=config.backend)
        root_collection_id = _populate_database(
            config=config, image_path=image_path, dataset_name=dataset_name
        )
        _verify_annotation_counts(
            collection_id=root_collection_id,
            boxes_per_image=config.boxes_per_image,
        )

        preview_server = Server(host=config.host, port=config.port)
        setup_elapsed = time.perf_counter() - setup_started
        print(
            "Benchmark ready: "
            f"setup_time={setup_elapsed:.3f}s "
            f"db={db_target} "
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
    parser.add_argument(
        "--backend",
        choices=[backend.value for backend in Backend],
        default=Backend.DUCKDB.value,
        help=(
            "Database backend to populate. "
            "'duckdb' (default) uses a temporary DuckDB file. "
            "'postgres' (pgvector) uses $LIGHTLY_STUDIO_DATABASE_URL if set, otherwise "
            f"{DEFAULT_POSTGRES_URL}. "
            "'enterprise' connects to a remote instance via $LIGHTLY_STUDIO_API_URL "
            "and $LIGHTLY_STUDIO_TOKEN."
        ),
    )
    return parser.parse_args()


def _validate_config(config: BenchmarkConfig) -> None:
    """Validate the benchmark configuration."""
    if config.num_images <= 0:
        raise ValueError("--num-images must be greater than zero.")
    if config.boxes_per_image < 0:
        raise ValueError("--boxes-per-image must be zero or greater.")
    if config.image_width <= 0:
        raise ValueError("--image-width must be greater than zero.")
    if config.image_height <= 0:
        raise ValueError("--image-height must be greater than zero.")
    if config.batch_size <= 0:
        raise ValueError("--batch-size must be greater than zero.")


def _create_shared_image(image_path: Path, image_width: int, image_height: int) -> None:
    """Create a single image file reused by every sample."""
    Image.new("RGB", (image_width, image_height), color=(120, 120, 120)).save(image_path)


def _resolve_dataset_name(backend: Backend) -> str:
    """Resolve the root collection name for the run.

    The enterprise backend runs against a persistent remote database, so it uses a
    unique suffix per run to avoid colliding with the ``(name, parent_collection_id)``
    unique constraint on collections. A unique root collection also gets a fresh
    ``dataset_id``, which scopes the child annotation collection, embedding model, and
    annotation labels so they cannot collide either. The DuckDB and PostgreSQL backends
    start from a wiped database each run, so they keep the stable default name.
    """
    if backend is Backend.ENTERPRISE:
        return f"{DEFAULT_DATASET_NAME}_{uuid.uuid4().hex[:8]}"
    return DEFAULT_DATASET_NAME


def _resolve_id_offset(backend: Backend) -> int:
    """Return a per-run offset for the generated sample ids.

    Sample ids are built deterministically from a running integer via
    ``_make_uuid_str`` (0, 1, 2, ...). On the persistent enterprise database (which is
    not wiped) those would collide with rows from earlier runs on the ``sample`` primary
    key, so each run gets a random 64-bit high component, giving it a disjoint id block
    while keeping the fast id-generation path. The low 64 bits stay free for the running
    integer (well above any feasible row count), so the value stays within a UUID's 128
    bits. DuckDB and PostgreSQL start from a wiped database, so they keep a zero offset
    and their stable, deterministic ids.
    """
    if backend is Backend.ENTERPRISE:
        return secrets.randbits(64) << 64
    return 0


def _initialize_database(db_path: Path, backend: Backend) -> str:
    """Connect to the database and return a description of its target.

    Uses a temporary on-disk DuckDB by default, a local PostgreSQL container, or a
    remote enterprise instance. DuckDB and PostgreSQL are wiped and re-created; the
    enterprise backend connects via ``$LIGHTLY_STUDIO_API_URL`` /
    ``$LIGHTLY_STUDIO_TOKEN`` and is not wiped.
    """
    db_manager.close()
    if backend is Backend.ENTERPRISE:
        # Reads $LIGHTLY_STUDIO_API_URL and $LIGHTLY_STUDIO_TOKEN; delegates to
        # db_manager.connect without cleanup, so the remote database is not wiped.
        enterprise.connect()
        return os.environ.get("LIGHTLY_STUDIO_API_URL", "<enterprise>")
    if backend is Backend.POSTGRES:
        database_url = os.environ.get("LIGHTLY_STUDIO_DATABASE_URL", DEFAULT_POSTGRES_URL)
        db_manager.connect(db_url=database_url, cleanup_existing=True)
        return database_url
    db_manager.connect(db_file=str(db_path), cleanup_existing=True)
    return str(db_path)


def _populate_database(config: BenchmarkConfig, image_path: Path, dataset_name: str) -> UUID:
    """Populate the benchmark dataset with images, embeddings, and annotations."""
    rng = np.random.default_rng(config.seed)
    with db_manager.session() as session:
        root_collection = collection_resolver.create(
            session=session,
            collection=CollectionCreate(
                name=dataset_name,
                sample_type=SampleType.IMAGE,
            ),
        )
        annotation_collection_id = collection_resolver.get_or_create_child_collection(
            session=session,
            collection_id=root_collection.collection_id,
            sample_type=SampleType.ANNOTATION,
            name=DEFAULT_ANNOTATION_COLLECTION_NAME,
        )
        annotation_label_ids = [
            annotation_label_resolver.create(
                session=session,
                label=AnnotationLabelCreate(
                    dataset_id=root_collection.dataset_id,
                    annotation_label_name=name,
                ),
            ).annotation_label_id
            for name in DEFAULT_ANNOTATION_LABEL_NAMES
        ]
        root_collection_id = root_collection.collection_id
        embedding_model_id, embedding_dim = _resolve_embedding_model(
            session=session, collection_id=root_collection_id
        )

    raw_connection = db_manager.get_engine()._engine.raw_connection()
    try:
        connection = raw_connection.driver_connection
        if config.backend in (Backend.POSTGRES, Backend.ENTERPRISE):
            # Register pgvector adapters so embeddings stream via binary COPY.
            pgvector.psycopg.register_vector(connection)
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
                    embedding_dim=embedding_dim,
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


def _resolve_embedding_model(session: Session, collection_id: UUID) -> tuple[UUID, int]:
    """Resolve the embedding model the benchmark stores its embeddings under.

    Prefers the server's configured default embedding generator (e.g. MobileCLIP) so the
    embedding-model row's identity (name, file hash, and dimension) matches what *any*
    LightlyStudio server resolves as the collection's default — including a separate or
    deployed server. This is what makes the GUI's embeddings view appear there: the
    server falls back to that default generator and finds the embeddings stored under it.

    Loading the generator also registers it as the in-process default, so the benchmark's
    own GUI shows the view too. Returns the model id and the dimension the embeddings must
    have (dictated by the model, so the ``get_or_create`` hash/dimension check passes).

    Falls back to a synthetic model if no default generator is available; in that case the
    embeddings view only appears in this process's own GUI, not on a separate server.
    """
    embedding_manager = EmbeddingManagerProvider.get_embedding_manager()
    model_id = embedding_manager.load_or_get_default_model(
        session=session, collection_id=collection_id
    )
    if model_id is not None:
        model = embedding_model_resolver.get_by_id(session=session, embedding_model_id=model_id)
        assert model is not None, "Default embedding model just registered but not found."
        return model_id, model.embedding_dimension

    logger.warning(
        "No default embedding generator is available (set LIGHTLY_STUDIO_EMBEDDINGS_MODEL_TYPE "
        "and install the model package, e.g. MobileCLIP). Falling back to a synthetic embedding "
        "model: the embeddings view will appear in this process's GUI but not on a separate or "
        "deployed server."
    )
    synthetic_model = embedding_model_resolver.create(
        session=session,
        embedding_model=EmbeddingModelCreate(
            collection_id=collection_id,
            name=DEFAULT_EMBEDDING_MODEL_NAME,
            embedding_dimension=DEFAULT_EMBEDDING_DIM,
        ),
    )
    embedding_manager._collection_id_to_default_model_id[collection_id] = (
        synthetic_model.embedding_model_id
    )
    return synthetic_model.embedding_model_id, DEFAULT_EMBEDDING_DIM


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
    embedding_dim: int,
    annotation_label_ids: list[UUID],
    shared_image_path: Path,
) -> BatchData:
    """Build all Arrow tables for a batch."""
    image_id_strs = [_make_uuid_str(config.id_offset + batch_start + i) for i in range(batch_count)]

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
        embedding_dim=embedding_dim,
        embedding_model_id_str=str(embedding_model_id),
    )

    annotation_count = batch_count * config.boxes_per_image
    annotation_id_base = config.id_offset + config.num_images + batch_start * config.boxes_per_image
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
    """Insert an Arrow table into the target table, dispatching on the active backend."""
    if len(table) == 0:
        return
    # DuckDB connections expose zero-copy Arrow registration; psycopg (PostgreSQL) does not.
    if hasattr(connection, "register"):
        _insert_arrow_table_duckdb(connection=connection, table=table, spec=spec)
    else:
        _insert_arrow_table_postgres(connection=connection, table=table, spec=spec)


def _insert_arrow_table_duckdb(
    connection: object,
    table: pa.Table,
    spec: ArrowInsertSpec,
) -> None:
    """Register an Arrow table in DuckDB and INSERT it into the target table."""
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


# UUID-typed columns inserted by the benchmark; psycopg binds real UUID objects, not strings.
_UUID_INSERT_COLUMNS = frozenset(
    {
        "sample_id",
        "collection_id",
        "embedding_model_id",
        "annotation_label_id",
        "parent_sample_id",
    }
)


def _insert_arrow_table_postgres(
    connection: object,
    table: pa.Table,
    spec: ArrowInsertSpec,
) -> None:
    """Bulk-load an Arrow table into PostgreSQL via ``COPY`` (psycopg has no Arrow path).

    ``COPY ... FROM STDIN`` is far faster than per-row ``executemany`` for large loads.
    The only SQL literal in ``select_columns_sql`` is ``current_timestamp``; since
    ``COPY`` streams literal values rather than SQL expressions, those columns are
    filled with a single Python timestamp captured per batch. Postgres applies each
    column's input function to the text we stream, so the enum columns are loaded from
    their text representation without explicit casts.
    """
    if "embedding" in table.column_names:
        # The embeddings table dominates load time at scale; stream it via pgvector's
        # binary protocol to skip building a float-vector string per row.
        _copy_embeddings_postgres(connection=connection, table=table, spec=spec)
        return

    source_cols = table.column_names
    insert_cols = spec.insert_columns or tuple(source_cols)
    select_terms = (
        [term.strip() for term in spec.select_columns_sql.split(",")]
        if spec.select_columns_sql
        else list(source_cols)
    )
    created_at = datetime.now(timezone.utc)
    copy_sql = f"COPY {spec.table_name} ({', '.join(insert_cols)}) FROM STDIN"

    cursor = connection.cursor()  # type: ignore[attr-defined]
    try:
        with cursor.copy(copy_sql) as copy:
            for row in table.to_pylist():
                copy.write_row(
                    [
                        _to_postgres_value(column=term, value=row[term])
                        if term in source_cols
                        else created_at
                        for term in select_terms
                    ]
                )
    finally:
        cursor.close()


_EMBEDDING_COPY_TYPES = {
    "sample_id": "uuid",
    "embedding_model_id": "uuid",
    "embedding": "vector",
}


def _copy_embeddings_postgres(
    connection: object,
    table: pa.Table,
    spec: ArrowInsertSpec,
) -> None:
    """Bulk-load the embeddings table into PostgreSQL via pgvector's binary ``COPY``.

    The embedding column is read as a ``(n, dim)`` float32 numpy array (a near
    zero-copy view of the Arrow buffer) and streamed with pgvector's binary dumper.
    This avoids materializing a Python list and a comma-joined string per row, which
    is the dominant cost of loading high-dimensional embeddings.
    """
    insert_cols = spec.insert_columns or tuple(table.column_names)
    row_count = len(table)
    embeddings = (
        table.column("embedding").combine_chunks().flatten().to_numpy(zero_copy_only=False)
    ).reshape(row_count, -1)
    column_values: dict[str, Any] = {
        "sample_id": [UUID(value) for value in table.column("sample_id").to_pylist()],
        "embedding_model_id": [
            UUID(value) for value in table.column("embedding_model_id").to_pylist()
        ],
        "embedding": embeddings,
    }

    copy_sql = f"COPY {spec.table_name} ({', '.join(insert_cols)}) FROM STDIN WITH (FORMAT BINARY)"
    cursor = connection.cursor()  # type: ignore[attr-defined]
    try:
        with cursor.copy(copy_sql) as copy:
            copy.set_types([_EMBEDDING_COPY_TYPES[col] for col in insert_cols])
            for index in range(row_count):
                copy.write_row([column_values[col][index] for col in insert_cols])
    finally:
        cursor.close()


def _to_postgres_value(column: str, value: Any) -> Any:
    """Adapt an Arrow cell to the value streamed via ``COPY`` for the target column."""
    if column in _UUID_INSERT_COLUMNS:
        return UUID(str(value))
    return value


if __name__ == "__main__":
    main()
