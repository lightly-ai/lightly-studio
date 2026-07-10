# PRD — Metadata-Driven Sampling & Visualization (custom demo branch)

**Branch:** `jonas-metadata-prototype-plot-sample`
**Status:** Draft
**Scope note:** This is a **bespoke demo branch**, not intended to merge to `main` as-is.
Bias every implementation decision toward **reuse and minimal surface area** over
generality. Hardcoding sensible defaults is acceptable; heavy config, exhaustive
edge-case handling, and broad test suites are out of scope unless a change would
otherwise break existing behavior. Keep new code isolated so it is easy to delete later.

## Background

`lightly_studio` (Python/FastAPI + SQLModel backend, SvelteKit frontend) lets users
sample and explore image/video datasets. This branch adds four metadata-driven
capabilities for a custom project.

### Data reality this is designed for
- ~5–10 **categorical** metadata keys, each with cardinality up to ~10.
- ~10 **numerical** metadata keys (integer/float).
- **GPS** present as the `gps_coordinate` complex metadata type (`{lat, lon}`).
- ~**100k** samples per collection → backend aggregation for distributions/coloring;
  client-side is acceptable for the GPS scatter (all coords held client-side).

### Key facts about the current system (from codebase exploration)
- **Balance sampling** is annotation-coupled: `AnnotationClassBalancingStrategy`
  (`sampling/sampling_config.py`) → `annotation_label_id`, resolved in
  `sampling/sampling_via_db.py` → `mundig.add_class_balancing(matrix, target, strength)`.
  The Mundig mechanism (per-sample distribution matrix + target vector) is **generic**.
  Strategies are a Pydantic discriminated union + `isinstance` dispatch — no registry.
- **Metadata** is schemaless per-sample JSON (`SampleMetadataTable`, `models/metadata.py`)
  with a per-key inferred type string (`boolean/integer/float/string/list/dict` and the
  complex `gps_coordinate`). There is **no "categorical" type** — categorical = `string`
  (or `boolean`). Only numeric **min/max** is aggregated today (`get_metadata_info`);
  there is **no distinct-value / count aggregation endpoint**.
- **Distribution UI** already exists on this branch: `DatasetDistributionPanel` +
  ECharts `BarChart`, with `DistributionSource.groups` scaffolded for "one entry per
  metadata key" but only wired for annotation-type distributions. **No histogram** yet.
- **Embedding plot** uses `embedding-atlas` (`EmbeddingView`, WebGPU) in `PlotPanel.svelte`.
  Data arrives as an **Apache Arrow IPC stream** (`x, y, fulfils_filter,
  color_categories:list<uint8>, sample_id`, plus `color_legend` in schema metadata).
  Color-by supports `annotation_label | tags | metadata`. Colors are generated
  frontend-side on an **OKLCH hue wheel** (nominal). Rect/lasso select →
  `sampleId`s pushed into the shared active filter.
- **Embedding metadata coloring** (`embedding_coloring/metadata.py`) supports
  `string`/`boolean` (frequency-ordered + "Other") and `integer` (range buckets), but
  **raises "unsupported type" for `float`** and for `gps_coordinate`.
- **No map/GPS rendering exists** — no Leaflet/Mapbox/MapLibre/deck.gl anywhere.

## Features

1. **Categorical-metadata balance sampling** — extend balance sampling (today
   annotation-only) to a single categorical metadata key.
2. **Metadata distribution plots with set comparison** — bar charts (categorical) and
   histograms (numerical) that can overlay multiple **tags** for comparison.
3. **Interactive GPS map** — real basemap with rectangle-select that drives the shared
   filter; points colored by selected tags.
4. **Numeric-metadata coloring of the embedding plot** — make `float`/`integer`
   coloring work using an ordered, gradient (sequential) color ramp.

## Cross-cutting decisions

- **Missing/null metadata values** handled consistently:
  - **Balance:** samples missing the key are **excluded from that strategy's influence**
    (zero contribution), matching how annotation balancing ignores samples without the
    annotation.
  - **Distribution:** show an explicit **`(none)`** bar/bin so coverage gaps are visible.
  - **Coloring:** points missing the value are **dim gray** (`UNASSIGNED_COLOR`), never
    silently hidden.
- **Binning differs by purpose:**
  - Coloring (Feature 4): **quantile** bins (equal sample counts → good color contrast).
  - Histogram (Feature 2): **equal-width** bins (~25) to reveal distribution shape;
    edges computed over the **global** range across all compared tags so series share an x-axis.

## Shared foundation (build first)

A single **unified distribution/aggregation endpoint** plus a metadata-info extension,
reused by Features 1, 2, and gating Feature 3. See `ISSUE-0-shared-foundation.md`.

## Build order / issues

0. `ISSUE-0-shared-foundation.md` — unified aggregation endpoint + metadata-info extension.
1. `ISSUE-4-numeric-coloring.md` — numeric embedding coloring (small, self-contained).
2. `ISSUE-1-categorical-balance.md` — categorical balance strategy.
3. `ISSUE-2-distribution-comparison.md` — distribution panel extension + histogram + tag compare.
4. `ISSUE-3-gps-map.md` — MapLibre GPS map.
5. `ISSUE-5-wiring-qa.md` — end-to-end wiring pass and manual QA.

## Non-goals
- Merging to `main`; production hardening; multi-key (joint) balancing (stack single-key
  strategies instead); continuous colorbar (buckets only); offline/self-hosted map tiles;
  polygon/lasso select on the map (rectangle only); user-configurable histogram bin counts.
