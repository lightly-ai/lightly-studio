from __future__ import annotations

import argparse
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np
from sqlalchemy import ARRAY, Column, Float, Integer, LargeBinary, create_engine, func, insert, select
from sqlalchemy.orm import DeclarativeBase, Session


class Base(DeclarativeBase):
    pass


class ArrayEmbedding(Base):
    __tablename__ = "array_embedding"

    sample_id = Column(Integer, primary_key=True, autoincrement=False)
    embedding = Column(ARRAY(Float), nullable=False)


class BlobEmbedding(Base):
    __tablename__ = "blob_embedding"

    sample_id = Column(Integer, primary_key=True, autoincrement=False)
    embedding_blob = Column(LargeBinary, nullable=False)


class MatrixEmbeddingBlob(Base):
    __tablename__ = "matrix_embedding_blob"

    matrix_id = Column(Integer, primary_key=True, autoincrement=False)
    num_embeddings = Column(Integer, nullable=False)
    dim = Column(Integer, nullable=False)
    matrix_blob = Column(LargeBinary, nullable=False)


@dataclass(frozen=True)
class SearchResult:
    sample_ids: np.ndarray
    similarities: np.ndarray


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Benchmark cosine top-k search in DuckDB (ARRAY + list_cosine_distance) "
            "vs Python/NumPy (BLOB + decode)."
        )
    )
    parser.add_argument("--num-embeddings", type=int, default=50_000)
    parser.add_argument("--dim", type=int, default=512)
    parser.add_argument("--top-k", type=int, default=100)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=2_000)
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument(
        "--skip-blob-from-db",
        action="store_true",
        help=(
            "Skip the full option-b benchmark that reloads and decodes all BLOBs from DuckDB "
            "for every query."
        ),
    )
    parser.add_argument(
        "--skip-matrix-blob-from-db",
        action="store_true",
        help=(
            "Skip option-c benchmark that reloads and decodes one big matrix BLOB from DuckDB "
            "for every query."
        ),
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path("benchmark_sim_search/sim_search_benchmark.duckdb"),
    )
    return parser.parse_args()


def generate_embeddings(*, num_embeddings: int, dim: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed=seed)
    embeddings = rng.standard_normal(size=(num_embeddings, dim), dtype=np.float32)
    return embeddings


def _batch_ranges(total: int, batch_size: int) -> list[tuple[int, int]]:
    return [
        (start, min(start + batch_size, total))
        for start in range(0, total, batch_size)
    ]


def insert_array_embeddings(
    *,
    session: Session,
    embeddings: np.ndarray,
    batch_size: int,
) -> None:
    num_embeddings = embeddings.shape[0]
    insert_stmt = insert(ArrayEmbedding)
    with session.begin():
        for start, end in _batch_ranges(total=num_embeddings, batch_size=batch_size):
            batch_embeddings = embeddings[start:end].tolist()
            rows = [
                {
                    "sample_id": sample_id,
                    "embedding": embedding,
                }
                for sample_id, embedding in enumerate(batch_embeddings, start=start)
            ]
            session.execute(insert_stmt, rows)


def insert_blob_embeddings(
    *,
    session: Session,
    embeddings: np.ndarray,
    batch_size: int,
) -> None:
    num_embeddings = embeddings.shape[0]
    insert_stmt = insert(BlobEmbedding)
    with session.begin():
        for start, end in _batch_ranges(total=num_embeddings, batch_size=batch_size):
            rows = [
                {
                    "sample_id": sample_id,
                    "embedding_blob": embeddings[sample_id].tobytes(order="C"),
                }
                for sample_id in range(start, end)
            ]
            session.execute(insert_stmt, rows)


def insert_matrix_blob(
    *,
    session: Session,
    embeddings: np.ndarray,
) -> None:
    num_embeddings, dim = embeddings.shape
    matrix_bytes = np.ascontiguousarray(embeddings, dtype=np.float32).tobytes(order="C")
    insert_stmt = insert(MatrixEmbeddingBlob)
    with session.begin():
        session.execute(
            insert_stmt,
            [
                {
                    "matrix_id": 1,
                    "num_embeddings": num_embeddings,
                    "dim": dim,
                    "matrix_blob": matrix_bytes,
                }
            ],
        )


def db_array_topk(
    *,
    session: Session,
    query_embedding: np.ndarray,
    top_k: int,
) -> SearchResult:
    query_list = query_embedding.tolist()
    distance_expr = func.list_cosine_distance(ArrayEmbedding.embedding, query_list)
    similarity_expr = (1.0 - distance_expr).label("similarity")

    stmt = (
        select(ArrayEmbedding.sample_id, similarity_expr)
        .order_by(distance_expr)
        .limit(top_k)
    )
    rows = session.execute(stmt).all()
    sample_ids = np.array([row[0] for row in rows], dtype=np.int64)
    similarities = np.array([row[1] for row in rows], dtype=np.float32)
    return SearchResult(sample_ids=sample_ids, similarities=similarities)


def load_blob_matrix(*, session: Session, dim: int) -> tuple[np.ndarray, np.ndarray]:
    rows = session.execute(
        select(BlobEmbedding.sample_id, BlobEmbedding.embedding_blob).order_by(
            BlobEmbedding.sample_id
        )
    ).all()
    sample_ids = np.array([row[0] for row in rows], dtype=np.int64)
    matrix = np.stack(
        [np.frombuffer(row[1], dtype=np.float32, count=dim) for row in rows],
        axis=0,
    )
    return sample_ids, matrix


def load_matrix_blob(*, session: Session) -> tuple[np.ndarray, np.ndarray]:
    row = session.execute(
        select(
            MatrixEmbeddingBlob.num_embeddings,
            MatrixEmbeddingBlob.dim,
            MatrixEmbeddingBlob.matrix_blob,
        )
        .where(MatrixEmbeddingBlob.matrix_id == 1)
        .limit(1)
    ).first()
    if row is None:
        raise RuntimeError("No matrix blob row found in matrix_embedding_blob table.")

    num_embeddings, dim, matrix_blob = row
    sample_ids = np.arange(num_embeddings, dtype=np.int64)
    matrix = np.frombuffer(
        matrix_blob,
        dtype=np.float32,
        count=num_embeddings * dim,
    ).reshape(num_embeddings, dim)
    return sample_ids, matrix


def numpy_topk(
    *,
    sample_ids: np.ndarray,
    matrix: np.ndarray,
    matrix_norms: np.ndarray,
    query_embedding: np.ndarray,
    top_k: int,
) -> SearchResult:
    safe_top_k = min(top_k, matrix.shape[0])
    query_norm = np.linalg.norm(query_embedding)
    similarities = (matrix @ query_embedding) / np.maximum(matrix_norms * query_norm, 1e-12)

    top_idx = np.argpartition(similarities, -safe_top_k)[-safe_top_k:]
    sorted_idx = top_idx[np.argsort(similarities[top_idx])[::-1]]

    return SearchResult(
        sample_ids=sample_ids[sorted_idx],
        similarities=similarities[sorted_idx],
    )


def blob_python_topk_from_db(
    *,
    session: Session,
    dim: int,
    query_embedding: np.ndarray,
    top_k: int,
) -> SearchResult:
    sample_ids, matrix = load_blob_matrix(session=session, dim=dim)
    matrix_norms = np.linalg.norm(matrix, axis=1)
    return numpy_topk(
        sample_ids=sample_ids,
        matrix=matrix,
        matrix_norms=matrix_norms,
        query_embedding=query_embedding,
        top_k=top_k,
    )


def matrix_blob_python_topk_from_db(
    *,
    session: Session,
    query_embedding: np.ndarray,
    top_k: int,
) -> SearchResult:
    sample_ids, matrix = load_matrix_blob(session=session)
    matrix_norms = np.linalg.norm(matrix, axis=1)
    return numpy_topk(
        sample_ids=sample_ids,
        matrix=matrix,
        matrix_norms=matrix_norms,
        query_embedding=query_embedding,
        top_k=top_k,
    )


def _time_it(fn: Callable[[], Any]) -> tuple[float, Any]:
    start = time.perf_counter()
    result = fn()
    duration_s = time.perf_counter() - start
    return duration_s, result


def print_results(
    *,
    db_times_s: list[float],
    numpy_in_memory_times_s: list[float],
    numpy_from_db_times_s: list[float] | None,
    numpy_matrix_blob_from_db_times_s: list[float] | None,
    setup_times_s: dict[str, float],
    num_embeddings: int,
    dim: int,
    top_k: int,
    repeats: int,
) -> None:
    db_mean_ms = statistics.mean(db_times_s) * 1_000
    np_in_memory_mean_ms = statistics.mean(numpy_in_memory_times_s) * 1_000
    db_median_ms = statistics.median(db_times_s) * 1_000
    np_in_memory_median_ms = statistics.median(numpy_in_memory_times_s) * 1_000
    np_from_db_mean_ms = None
    np_from_db_median_ms = None
    np_matrix_blob_from_db_mean_ms = None
    np_matrix_blob_from_db_median_ms = None
    if numpy_from_db_times_s:
        np_from_db_mean_ms = statistics.mean(numpy_from_db_times_s) * 1_000
        np_from_db_median_ms = statistics.median(numpy_from_db_times_s) * 1_000
    if numpy_matrix_blob_from_db_times_s:
        np_matrix_blob_from_db_mean_ms = statistics.mean(numpy_matrix_blob_from_db_times_s) * 1_000
        np_matrix_blob_from_db_median_ms = statistics.median(numpy_matrix_blob_from_db_times_s) * 1_000

    print("\n=== Benchmark config ===")
    print(f"N={num_embeddings:,}, D={dim}, top_k={top_k}, repeats={repeats}")

    print("\n=== Setup ===")
    for key, value in setup_times_s.items():
        print(f"{key}: {value * 1_000:.2f} ms")

    print("\n=== Query times (per query) ===")
    print(
        f"DuckDB ARRAY + list_cosine_distance:    mean={db_mean_ms:.2f} ms, median={db_median_ms:.2f} ms"
    )
    if np_from_db_mean_ms is not None and np_from_db_median_ms is not None:
        print(
            "Python NumPy from BLOB (read+decode+search): "
            f"mean={np_from_db_mean_ms:.2f} ms, median={np_from_db_median_ms:.2f} ms"
        )
    if (
        np_matrix_blob_from_db_mean_ms is not None
        and np_matrix_blob_from_db_median_ms is not None
    ):
        print(
            "Python NumPy from one big matrix BLOB (read+decode+search): "
            f"mean={np_matrix_blob_from_db_mean_ms:.2f} ms, "
            f"median={np_matrix_blob_from_db_median_ms:.2f} ms"
        )
    print(
        "Python NumPy on preloaded BLOB matrix:       "
        f"mean={np_in_memory_mean_ms:.2f} ms, median={np_in_memory_median_ms:.2f} ms"
    )

    if db_mean_ms > 0:
        if np_from_db_mean_ms is not None:
            print(
                f"\nSlowdown NumPy-from-DB vs DuckDB (mean): {np_from_db_mean_ms / db_mean_ms:.2f}x"
            )
        if np_matrix_blob_from_db_mean_ms is not None:
            print(
                "Slowdown NumPy-from-one-big-BLOB vs DuckDB (mean): "
                f"{np_matrix_blob_from_db_mean_ms / db_mean_ms:.2f}x"
            )
        print(
            f"Slowdown NumPy-in-memory vs DuckDB (mean): {np_in_memory_mean_ms / db_mean_ms:.2f}x"
        )


def main() -> None:
    args = parse_args()

    if args.top_k <= 0:
        raise ValueError("--top-k must be > 0")
    if args.num_embeddings <= 0:
        raise ValueError("--num-embeddings must be > 0")
    if args.dim <= 0:
        raise ValueError("--dim must be > 0")

    embeddings = generate_embeddings(
        num_embeddings=args.num_embeddings,
        dim=args.dim,
        seed=args.seed,
    )

    db_path = args.db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"duckdb:///{db_path}")

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with Session(engine) as session:
        insert_array_s, _ = _time_it(
            lambda: insert_array_embeddings(
                session=session,
                embeddings=embeddings,
                batch_size=args.batch_size,
            )
        )
        insert_blob_s, _ = _time_it(
            lambda: insert_blob_embeddings(
                session=session,
                embeddings=embeddings,
                batch_size=args.batch_size,
            )
        )
        insert_matrix_blob_s, _ = _time_it(
            lambda: insert_matrix_blob(
                session=session,
                embeddings=embeddings,
            )
        )

        load_blob_s, loaded = _time_it(
            lambda: load_blob_matrix(
                session=session,
                dim=args.dim,
            )
        )
        blob_sample_ids, blob_matrix = loaded
        blob_norms = np.linalg.norm(blob_matrix, axis=1)

        rng = np.random.default_rng(seed=args.seed + 1)
        query_indices = rng.integers(
            low=0,
            high=args.num_embeddings,
            size=args.repeats,
        )

        db_times_s: list[float] = []
        numpy_in_memory_times_s: list[float] = []
        numpy_from_db_times_s: list[float] = []
        numpy_matrix_blob_from_db_times_s: list[float] = []

        for query_index in query_indices:
            query_embedding = embeddings[int(query_index)]

            db_time_s, db_result = _time_it(
                lambda: db_array_topk(
                    session=session,
                    query_embedding=query_embedding,
                    top_k=args.top_k,
                )
            )
            np_time_s, np_result = _time_it(
                lambda: numpy_topk(
                    sample_ids=blob_sample_ids,
                    matrix=blob_matrix,
                    matrix_norms=blob_norms,
                    query_embedding=query_embedding,
                    top_k=args.top_k,
                )
            )
            db_times_s.append(db_time_s)
            numpy_in_memory_times_s.append(np_time_s)

            if db_result.sample_ids[0] != np_result.sample_ids[0]:
                raise RuntimeError(
                    "Top-1 mismatch between DuckDB and NumPy results. "
                    "This benchmark assumes equivalent cosine ranking."
                )

            if not args.skip_blob_from_db:
                np_from_db_time_s, np_from_db_result = _time_it(
                    lambda: blob_python_topk_from_db(
                        session=session,
                        dim=args.dim,
                        query_embedding=query_embedding,
                        top_k=args.top_k,
                    )
                )
                numpy_from_db_times_s.append(np_from_db_time_s)
                if db_result.sample_ids[0] != np_from_db_result.sample_ids[0]:
                    raise RuntimeError(
                        "Top-1 mismatch between DuckDB and NumPy-from-DB results. "
                        "This benchmark assumes equivalent cosine ranking."
                    )

            if not args.skip_matrix_blob_from_db:
                np_matrix_blob_from_db_time_s, np_matrix_blob_from_db_result = _time_it(
                    lambda: matrix_blob_python_topk_from_db(
                        session=session,
                        query_embedding=query_embedding,
                        top_k=args.top_k,
                    )
                )
                numpy_matrix_blob_from_db_times_s.append(np_matrix_blob_from_db_time_s)
                if db_result.sample_ids[0] != np_matrix_blob_from_db_result.sample_ids[0]:
                    raise RuntimeError(
                        "Top-1 mismatch between DuckDB and NumPy-from-one-big-BLOB results. "
                        "This benchmark assumes equivalent cosine ranking."
                    )

        setup_times_s = {
            "insert ARRAY(Float)": insert_array_s,
            "insert BLOB": insert_blob_s,
            "insert one big matrix BLOB": insert_matrix_blob_s,
            "load+decode BLOB matrix (one-time)": load_blob_s,
        }

    print_results(
        db_times_s=db_times_s,
        numpy_in_memory_times_s=numpy_in_memory_times_s,
        numpy_from_db_times_s=None if args.skip_blob_from_db else numpy_from_db_times_s,
        numpy_matrix_blob_from_db_times_s=(
            None if args.skip_matrix_blob_from_db else numpy_matrix_blob_from_db_times_s
        ),
        setup_times_s=setup_times_s,
        num_embeddings=args.num_embeddings,
        dim=args.dim,
        top_k=args.top_k,
        repeats=args.repeats,
    )


if __name__ == "__main__":
    main()
