# Benchmarks

Manual performance benchmarks for Lightly Studio. Each script is standalone and run with
`uv run` from the `lightly_studio` directory.

- [GUI benchmark](#gui-benchmark) — generate a synthetic dataset and drive the GUI/API.
- [Embedding I/O benchmark](#embedding-io-benchmark) — measure embedding insert and load
  performance at the database layer.
- [Tag assignment benchmark](#tag-assignment-benchmark) — measure bulk tag-assignment
  performance at the database layer.
- [Deep-copy benchmark](#deep-copy-benchmark) — measure collection deep-copy time and peak
  memory at enterprise scale.
- [Delete-dataset benchmark](#delete-dataset-benchmark) — measure dataset delete time and peak
  memory at enterprise scale.

## GUI benchmark

A script that generates a large synthetic dataset and starts the Lightly Studio GUI against it,
so you can measure frontend and API performance interactively.

### What it provides

- A configurable number of images (default 100 000) with random embeddings and object-detection
  annotations spread across five labels (`car`, `person`, `bicycle`, `truck`, `bus`).
- Image width and height are drawn uniformly at random between 500 px and 800 px, so the
  metadata filters in the sidebar are immediately useful.
- The dataset lives in a temporary directory and is deleted automatically when the process exits.

### Running the benchmark

From the `lightly_studio` directory:

```bash
uv run tests/benchmarks/gui_benchmark.py
```

Or from the repository root:

```bash
uv run --project lightly_studio lightly_studio/tests/benchmarks/gui_benchmark.py
```

When the dataset is ready, the script prints a line like:

```text
Benchmark ready: setup_time=12.345s db=/tmp/lightly_studio_gui_benchmark_abc123/benchmark.db url=http://localhost:8001
```

Open the printed URL in your browser.

#### Key options

| Flag | Default | Description |
|---|---|---|
| `--num-images` | 100 000 | Number of images to generate |
| `--boxes-per-image` | 10 | Object-detection boxes per image |
| `--embedding-dim` | 512 | Embedding vector dimensionality |
| `--batch-size` | 5 000 | Insertion batch size |
| `--seed` | 0 | Random seed for reproducibility |
| `--host` | auto | Host to bind the server to |
| `--port` | auto | Port to bind the server to |
| `--postgres` | off | Populate PostgreSQL (pgvector) instead of the temporary DuckDB |

Example with a smaller dataset for a quick smoke-test:
```bash
uv run tests/benchmarks/gui_benchmark.py --num-images 10000
```

Same for postgres:
```bash
make start-postgres
uv run tests/benchmarks/gui_benchmark.py --num-images 10000 --postgres
make stop-postgres
```

### Measuring performance

1. Open the GUI URL in Chrome (or any Chromium-based browser).
2. Open **DevTools** (`F12` or `Cmd+Option+I`) and switch to the **Network** tab.
3. Enable **Disable cache** so responses are not served from the browser cache.
4. Interact with the GUI — scroll the grid, apply label/metadata filters, toggle embeddings — and
   observe the duration of each API request in the Network panel.

#### Simulating a slow connection

To surface latency-sensitive issues, throttle the network inside DevTools
(see also: [Chrome DevTools Network Throttling](https://www.debugbear.com/blog/chrome-devtools-network-throttling)):

1. In the Network tab, open the throttle dropdown (defaults to **No throttling**).
2. Select a preset such as **Slow 4G** (~1.6 Mbps down, 750 ms RTT).
3. Repeat your interactions and compare request durations.

This is especially useful for validating pagination, lazy loading of images, and embedding-scatter
responsiveness under realistic network conditions.

## Embedding I/O benchmark

A script that measures the database code paths for storing and loading sample embeddings:
inserting via `sample_embedding_resolver.create_many` and loading back via
`sample_embedding_resolver.get_by_sample_ids`. Unlike the GUI benchmark, which populates data
through a fast Arrow path, this benchmark exercises the regular resolver paths, so it reflects the
performance the application actually sees.

For each phase it reports wall-clock time, throughput, and **peak Python allocation**
(via `tracemalloc`). Peak memory is the key metric: a `list[float]` representation costs ~50 B per
element versus 4 B for a numpy `float32` buffer, so the load phase is where the in-memory
representation matters most.

### Running the benchmark

From the `lightly_studio` directory (temporary DuckDB by default):

```bash
uv run tests/benchmarks/embedding_io_benchmark.py
```

Against PostgreSQL (pgvector):

```bash
make start-postgres
uv run tests/benchmarks/embedding_io_benchmark.py --postgres
make stop-postgres
```

A quick smoke-test with a smaller dataset:

```bash
uv run tests/benchmarks/embedding_io_benchmark.py --num-embeddings 10000
```

### Key options

| Flag | Default | Description |
|---|---|---|
| `--num-embeddings` | 100 000 | Number of embeddings to insert and load |
| `--embedding-dim` | 512 | Embedding vector dimensionality |
| `--insert-batch-size` | 1 024 | Embeddings inserted per `create_many` call |
| `--seed` | 0 | Random seed for reproducibility |
| `--postgres` | off | Benchmark PostgreSQL (pgvector) instead of the temporary DuckDB |

## Tag assignment benchmark

A script that measures the database code path for assigning a tag to many samples:
`tag_resolver.add_sample_ids_to_tag_id`. It reproduces the slowdown described in LIG-9850, where the
original implementation issued one `session.merge` round-trip per sample id, so the GUI "add to tag"
action could run for minutes on large datasets.

For each phase it reports wall-clock time, throughput, and **peak Python allocation** (via
`tracemalloc`):

- **assign** — assign the tag to all samples (the main operation).
- **reassign** — repeat the call with the same sample ids; this exercises the idempotent
  conflict-handling path (already-tagged samples) and the script verifies that no duplicate links were
  created.

### Running the benchmark

From the `lightly_studio` directory (temporary DuckDB by default):

```bash
uv run tests/benchmarks/tag_assignment_benchmark.py
```

Against PostgreSQL:

```bash
make start-postgres
uv run tests/benchmarks/tag_assignment_benchmark.py --postgres
make stop-postgres
```

A quick smoke-test with a smaller dataset:

```bash
uv run tests/benchmarks/tag_assignment_benchmark.py --num-samples 10000
```

### Key options

| Flag | Default | Description |
|---|---|---|
| `--num-samples` | 100 000 | Number of samples to create and tag |
| `--postgres` | off | Benchmark PostgreSQL instead of the temporary DuckDB |

## Deep-copy benchmark

A script that times `dataset_resolver.deep_copy` and reports wall-clock time and **peak Python
allocation**. `deep_copy` is enterprise-only and runs the copy server-side via `INSERT ... SELECT`,
so it only supports PostgreSQL and peak Python memory should stay low (a few MiB) regardless of
dataset size — that is the key signal that no rows are materialized in Python.

It has two modes: generate a synthetic dataset of images with embeddings and copy it, or copy an
existing root collection (e.g. the COCO demo on an enterprise database, which also exercises the
annotation copy paths).

### Running the benchmark

From the `lightly_studio` directory, against a running Postgres:

```bash
make start-postgres
uv run tests/benchmarks/deep_copy_benchmark.py --generate 250000
make stop-postgres
```

A quick smoke-test with a smaller dataset:

```bash
uv run tests/benchmarks/deep_copy_benchmark.py --generate 10000
```

Copy an existing collection (uses `$LIGHTLY_STUDIO_DATABASE_URL` as-is, no cleanup):

```bash
LIGHTLY_STUDIO_DATABASE_URL=<postgres-url> \
    uv run tests/benchmarks/deep_copy_benchmark.py --collection-name "coco" --copy-name "coco_copy"
```

`--generate` recreates the database at `$LIGHTLY_STUDIO_DATABASE_URL` (or the default dev URL);
scale `--generate` toward 1M+ for the enterprise target.

### Key options

| Flag | Default | Description |
|---|---|---|
| `--generate N` | — | Generate N images with embeddings, then copy them |
| `--collection-name NAME` | — | Copy an existing root collection instead (mutually exclusive with `--generate`) |
| `--copy-name NAME` | `deep_copy_benchmark_copy` | Name for the copied root collection (must not already exist) |
| `--embedding-dim` | 512 | Embedding vector dimensionality (generate mode) |
| `--batch-size` | 5 000 | Generation batch size |
| `--seed` | 0 | Random seed for reproducibility |

## Delete-dataset benchmark

A script that times `dataset_resolver.delete_dataset` and reports wall-clock time and **peak Python
allocation**. `delete_dataset` is enterprise-only and runs server-side via subquery-scoped
`DELETE`s in a single transaction, so it only supports PostgreSQL and peak Python memory should stay
low (a few MiB) regardless of dataset size — that is the key signal that no rows are materialized in
Python.

It has two modes: generate a synthetic dataset of images with embeddings and delete it, or delete an
existing root collection by name (e.g. the COCO demo on an enterprise database, which also exercises
the annotation/video/evaluation delete paths).

### Running the benchmark

From the `lightly_studio` directory, against a running Postgres:

```bash
make start-postgres
uv run tests/benchmarks/delete_dataset_benchmark.py --generate 250000
make stop-postgres
```

A quick smoke-test with a smaller dataset:

```bash
uv run tests/benchmarks/delete_dataset_benchmark.py --generate 10000
```

Delete an existing collection (uses `$LIGHTLY_STUDIO_DATABASE_URL` as-is, no cleanup):

```bash
LIGHTLY_STUDIO_DATABASE_URL=<postgres-url> \
    uv run tests/benchmarks/delete_dataset_benchmark.py --collection-name "coco"
```

> **Warning:** `--collection-name` is destructive — it permanently deletes the named collection and
> all its data from the configured database. Use it only against a database you are willing to mutate
> (e.g. a throwaway copy), not one whose data you want to keep.

`--generate` recreates the database at `$LIGHTLY_STUDIO_DATABASE_URL` (or the default dev URL); scale
`--generate` toward 1M+ for the enterprise target.

### Key options

| Flag | Default | Description |
|---|---|---|
| `--generate N` | — | Generate N images with embeddings, then delete them |
| `--collection-name NAME` | — | Permanently delete an existing root collection instead (destructive; mutually exclusive with `--generate`) |
| `--embedding-dim` | 512 | Embedding vector dimensionality (generate mode) |
| `--batch-size` | 5 000 | Generation batch size |
| `--seed` | 0 | Random seed for reproducibility |
