# Benchmarks

Manual performance benchmarks for Lightly Studio. Each script is standalone and run with
`uv run` from the `lightly_studio` directory.

- [GUI benchmark](#gui-benchmark) — generate a synthetic dataset and drive the GUI/API.
- [Embedding I/O benchmark](#embedding-io-benchmark) — measure embedding insert and load
  performance at the database layer.

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

### Interpreting the results

The backends differ in how they return vectors, which shows up clearly in the load phase:

- **DuckDB** (`ARRAY(Float)`) returns Python `list[float]`, so load peak memory is high.
- **PostgreSQL** (pgvector) returns numpy arrays, so load peak memory is much lower.

Insert is CPU/DB-bound rather than memory-bound (each batch is freed before the next), so its peak
memory stays low on both backends.
