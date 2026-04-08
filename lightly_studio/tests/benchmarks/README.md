# GUI Benchmark

A script that generates a large synthetic dataset and starts the Lightly Studio GUI against it,
so you can measure frontend and API performance interactively.

## What it provides

- A configurable number of images (default 100 000) with random embeddings and object-detection
  annotations spread across five labels (`car`, `person`, `bicycle`, `truck`, `bus`).
- Image width and height are drawn uniformly at random between 500 px and 800 px, so the
  metadata filters in the sidebar are immediately useful.
- The dataset lives in a temporary directory and is deleted automatically when the process exits.

## Running the benchmark

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

### Key options

| Flag | Default | Description |
|---|---|---|
| `--num-images` | 100 000 | Number of images to generate |
| `--boxes-per-image` | 10 | Object-detection boxes per image |
| `--embedding-dim` | 512 | Embedding vector dimensionality |
| `--batch-size` | 5 000 | Insertion batch size |
| `--seed` | 0 | Random seed for reproducibility |
| `--host` | auto | Host to bind the server to |
| `--port` | auto | Port to bind the server to |

Example with a smaller dataset for a quick smoke-test:

```bash
uv run tests/benchmarks/gui_benchmark.py --num-images 10000
```

## Measuring performance

1. Open the GUI URL in Chrome (or any Chromium-based browser).
2. Open **DevTools** (`F12` or `Cmd+Option+I`) and switch to the **Network** tab.
3. Enable **Disable cache** so responses are not served from the browser cache.
4. Interact with the GUI — scroll the grid, apply label/metadata filters, toggle embeddings — and
   observe the duration of each API request in the Network panel.

### Simulating a slow connection

To surface latency-sensitive issues, throttle the network inside DevTools
(see also: [Chrome DevTools Network Throttling](https://www.debugbear.com/blog/chrome-devtools-network-throttling)):

1. In the Network tab, open the throttle dropdown (defaults to **No throttling**).
2. Select a preset such as **Slow 4G** (~1.6 Mbps down, 750 ms RTT).
3. Repeat your interactions and compare request durations.

This is especially useful for validating pagination, lazy loading of images, and embedding-scatter
responsiveness under realistic network conditions.
