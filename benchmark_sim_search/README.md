# Similarity Search Benchmark

This folder contains a throwaway benchmark to compare cosine top-k search performance for two storage/query approaches in DuckDB via SQLAlchemy.

## Goal

Compare how fast it is to retrieve the top 100 nearest embeddings (with cosine similarity) for a random query embedding under two representations:

- `ARRAY(Float)` per sample, searched directly in DuckDB with `list_cosine_distance`.
- `BLOB` per sample (`float32` bytes), searched in Python/NumPy.

## Approach

- Generate `N` random embeddings as `float32` with shape `(N, 512)`.
- Store them twice in the same DuckDB database:
  - Table `array_embedding(sample_id, embedding FLOAT[])`
  - Table `blob_embedding(sample_id, embedding_blob BLOB)`
- Run cosine top-k (`k=100`) for random query embeddings.
- Report setup times and per-query times.

The benchmark currently measures three query paths:

- `DuckDB ARRAY + list_cosine_distance`:
  - Search fully in DB over `FLOAT[]` column.
- `Python NumPy from BLOB (read+decode+search)`:
  - For each query: load all blobs from DB, decode to `float32` matrix, compute cosine in NumPy.
- `Python NumPy on preloaded BLOB matrix`:
  - Load/decode once, then query in-memory matrix only.

Notes:

- The script checks top-1 ID consistency between methods.
- This is exact brute-force cosine search in all paths (no ANN index).

## Run

From this directory:

```bash
python benchmark.py --num-embeddings=200000 --repeats=2
```

Useful flags:

- `--num-embeddings` (default: `50000`)
- `--dim` (default: `512`)
- `--top-k` (default: `100`)
- `--repeats` (default: `5`)
- `--batch-size` (default: `2000`)
- `--skip-blob-from-db` to skip per-query DB reload for blob path

## Results (example run)

Command:

```bash
python benchmark.py --num-embeddings=200000 --repeats=2
```

Output summary:

| Metric | Value |
| --- | ---: |
| N, D, top-k | 200,000, 512, 100 |
| insert ARRAY(Float) | 26,000.06 ms |
| insert BLOB | 2,211.51 ms |
| load+decode BLOB matrix (one-time) | 560.80 ms |
| DuckDB ARRAY query (mean/query) | 201.15 ms |
| NumPy from BLOB (read+decode+search, mean/query) | 755.30 ms |
| NumPy on preloaded matrix (mean/query) | 11.63 ms |
| Slowdown NumPy-from-DB vs DuckDB | 3.75x |
| Slowdown NumPy-in-memory vs DuckDB | 0.06x |

## Interpretation

- Writing embeddings as `BLOB` is much faster than writing `ARRAY(Float)`.
- Querying from `BLOB` by reloading/decoding every query is much slower than DB-side array search.
- NumPy cosine compute itself is very fast when embeddings are already in memory.
- For repeated queries in the same process, preloading can dominate after only a few queries.

Given the numbers above, preloading + in-memory NumPy becomes cheaper than DB array search after roughly 3 queries:

- Preloaded path total: `561 ms + q * 11.63 ms`
- DB array path total: `q * 201.15 ms`

## Caveats

- `repeats=2` is noisy; increase to `20+` for more stable medians.
- Benchmark reflects this machine, this DuckDB version, and brute-force search only.
- No concurrency or API overhead is included.
