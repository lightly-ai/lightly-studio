# Similarity Search Benchmark

This folder contains a throwaway benchmark to compare cosine top-k search performance for three storage/query approaches in DuckDB via SQLAlchemy.

## Goal

Compare how fast it is to retrieve the top 100 nearest embeddings (with cosine similarity) for a random query embedding under three representations:

- `ARRAY(Float)` per sample, searched directly in DuckDB with `list_cosine_distance`.
- `BLOB` per sample (`float32` bytes), searched in Python/NumPy.
- one big matrix `BLOB` containing all embeddings (`(N, D)`), searched in Python/NumPy.

## Approach

- Generate `N` random embeddings as `float32` with shape `(N, 512)`.
- Store them in three formats in the same DuckDB database:
  - Table `array_embedding(sample_id, embedding FLOAT[])`
  - Table `blob_embedding(sample_id, embedding_blob BLOB)`
  - Table `matrix_embedding_blob(matrix_id, num_embeddings, dim, matrix_blob BLOB)`
- Run cosine top-k (`k=100`) for random query embeddings.
- Report setup times and per-query times.

The benchmark currently measures four query paths:

- `DuckDB ARRAY + list_cosine_distance`:
  - Search fully in DB over `FLOAT[]` column.
- `Python NumPy from BLOB (read+decode+search)`:
  - For each query: load all blobs from DB, decode to `float32` matrix, compute cosine in NumPy.
- `Python NumPy on preloaded BLOB matrix`:
  - Load/decode once, then query in-memory matrix only.
- `Python NumPy from one big matrix BLOB (read+decode+search)`:
  - For each query: load one row containing all embeddings, decode to `float32` matrix, compute cosine in NumPy.

Notes:

- The script checks top-1 ID consistency between methods.
- This is exact brute-force cosine search in all paths (no ANN index).

## Run

From this directory:

```bash
python benchmark.py --num-embeddings=1000000 --repeats=10
```

Useful flags:

- `--num-embeddings` (default: `50000`)
- `--dim` (default: `512`)
- `--top-k` (default: `100`)
- `--repeats` (default: `5`)
- `--batch-size` (default: `2000`)
- `--skip-blob-from-db` to skip per-query DB reload for blob path
- `--skip-matrix-blob-from-db` to skip per-query DB reload for one-big-BLOB path

## Results (example run)

Command:

```bash
python benchmark.py --num-embeddings=1000000 --repeats=10
```

Output summary:

| Metric | Value |
| --- | ---: |
| N, D, top-k | 1,000,000, 512, 100 |
| insert ARRAY(Float) | 130,599.77 ms |
| insert BLOB | 12,356.57 ms |
| insert one big matrix BLOB | 5,184.88 ms |
| load+decode BLOB matrix (one-time) | 2,929.16 ms |
| DuckDB ARRAY query (mean/query) | 293.85 ms |
| NumPy from BLOB (read+decode+search, mean/query) | 3,441.09 ms |
| NumPy from one big matrix BLOB (read+decode+search, mean/query) | 1,323.67 ms |
| NumPy on preloaded matrix (mean/query) | 56.39 ms |
| Slowdown NumPy-from-DB vs DuckDB | 11.71x |
| Slowdown NumPy-from-one-big-BLOB vs DuckDB | 4.50x |
| Slowdown NumPy-in-memory vs DuckDB | 0.19x |

## Interpretation

- Writing embeddings as `BLOB` is much faster than writing `ARRAY(Float)`.
- Writing one big matrix `BLOB` is fastest at insert time.
- Querying from `BLOB` by reloading/decoding every query is much slower than DB-side array search.
- Querying from one big matrix `BLOB` per query is better than per-sample `BLOB`, but still slower than DB-side array search.
- NumPy cosine compute itself is very fast when embeddings are already in memory.
- For repeated queries in the same process, preloading can dominate after only a few queries.

Given the numbers above, preloading + in-memory NumPy becomes cheaper than DB array search after roughly 13 queries:

- Preloaded path total: `2,929 ms + q * 56.39 ms`
- DB array path total: `q * 293.85 ms`

## Caveats

- `repeats=10` is better, but still somewhat noisy; use larger repeat counts for tighter confidence.
- Benchmark reflects this machine, this DuckDB version, and brute-force search only.
- No concurrency or API overhead is included.
