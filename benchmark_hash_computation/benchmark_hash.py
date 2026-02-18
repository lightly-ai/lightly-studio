"""Benchmark: hash(embedding) vs embedding[1] for cache-key computation.

Compares the two approaches used in get_hash_by_sample_ids:
  Old: SELECT sample_id, hash(embedding) FROM ... → SHA256 in Python
  New: SELECT sample_id, embedding[1] FROM ...    → SHA256 in Python

Usage:
    cd lightly_studio
    uv run python ../benchmark_hash_computation/benchmark_hash.py
"""

import hashlib
import statistics
import time

import numpy as np
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session


# ── Constants (change here if needed) ────────────────────────────────────────
NUM_EMBEDDINGS = 50_000
DIM = 512
REPEATS = 5


# ── Benchmark functions ──────────────────────────────────────────────────────
def bench_old(session: Session) -> tuple[float, str]:
    """Old approach: hash(embedding) in DuckDB, then SHA256 in Python."""
    t0 = time.perf_counter()

    rows = session.execute(
        text("SELECT sample_id, hash(embedding) AS emb_hash "
             "FROM sample_embedding ORDER BY sample_id")
    ).all()

    hasher = hashlib.sha256()
    hasher.update("".join(str(row.emb_hash) for row in rows).encode("utf-8"))
    digest = hasher.hexdigest()

    elapsed_ms = (time.perf_counter() - t0) * 1000
    return elapsed_ms, digest


def bench_new(session: Session) -> tuple[float, str]:
    """New approach: embedding[1] in DuckDB, then SHA256 in Python."""
    t0 = time.perf_counter()

    rows = session.execute(
        text("SELECT sample_id, embedding[1] AS first_dim "
             "FROM sample_embedding ORDER BY sample_id")
    ).all()

    hasher = hashlib.sha256()
    hasher.update("".join(str(row.first_dim) for row in rows).encode("utf-8"))
    digest = hasher.hexdigest()

    elapsed_ms = (time.perf_counter() - t0) * 1000
    return elapsed_ms, digest


# ── Main ─────────────────────────────────────────────────────────────────────
def main() -> None:
    engine = create_engine("duckdb:///:memory:")

    # Create table and populate with random embeddings
    rng = np.random.default_rng(42)
    embeddings = rng.standard_normal((NUM_EMBEDDINGS, DIM)).astype(np.float32)

    with engine.connect() as conn:
        conn.execute(text(
            "CREATE TABLE sample_embedding (sample_id INTEGER PRIMARY KEY, embedding FLOAT[])"
        ))
        conn.commit()

    with Session(engine) as session:
        for i in range(NUM_EMBEDDINGS):
            session.execute(
                text("INSERT INTO sample_embedding VALUES (:sid, :emb)"),
                {"sid": i, "emb": embeddings[i].tolist()},
            )
        session.commit()

    print(f"\n=== Embedding Hash Benchmark ===")
    print(f"N={NUM_EMBEDDINGS:,}  dim={DIM}  repeats={REPEATS}\n")

    # ── Run benchmarks ───────────────────────────────────────────────────
    with Session(engine) as session:
        old_times: list[float] = []
        for _ in range(REPEATS):
            ms, digest_old = bench_old(session)
            old_times.append(ms)

        new_times: list[float] = []
        for _ in range(REPEATS):
            ms, digest_new = bench_new(session)
            new_times.append(ms)

    old_mean = statistics.mean(old_times)
    old_median = statistics.median(old_times)
    new_mean = statistics.mean(new_times)
    new_median = statistics.median(new_times)

    print(f"Old (hash(embedding)):   mean={old_mean:>8.2f} ms  median={old_median:>8.2f} ms")
    print(f"New (embedding[1]):      mean={new_mean:>8.2f} ms  median={new_median:>8.2f} ms")
    print(f"Speedup: {old_median / new_median:.2f}x\n")

    # Sanity check: repeated runs produce the same hash
    with Session(engine) as session:
        assert digest_old == bench_old(session)[1], "Old approach not deterministic!"
        assert digest_new == bench_new(session)[1], "New approach not deterministic!"
    print("Determinism check passed.")


if __name__ == "__main__":
    main()
