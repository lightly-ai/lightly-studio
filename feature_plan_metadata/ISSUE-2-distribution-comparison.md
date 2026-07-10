# Issue 2 — Metadata distribution plots with tag comparison

**Depends on:** Issue 0 (aggregation endpoint). **Blocks:** none.

## Goal
Show metadata distributions and let the user **overlay multiple tags** to compare them:
- **Categorical** keys → bar chart.
- **Numerical** keys → histogram (new render path).
- A **set = a tag**; the current filter/selection is available as one implicit series.

## Design decision
**Extend the existing `DatasetDistributionPanel`** (finishing the scaffolded
`DistributionSource.groups` "one entry per metadata key"), not a new panel.

## Rendering decisions
- **Normalization:** default to **percentage/density (normalized within each set)** so
  differently-sized tags are comparable; provide a **count/percentage toggle**.
- **Multi-series form:**
  - Categorical → **grouped bars** (one cluster per value, one bar per tag).
  - Numerical → **line/step density curves** when >1 series (readable for 3–4 series);
    keep filled bar/histogram for a single series.
- **Histogram bins:** **equal-width**, fixed **~25 bins**, edges computed over the
  **global** range of the key across all compared tags (shared x-axis). (Note: different
  from Feature 4's quantile bins — that's intentional.)
- **Missing values:** show an explicit **`(none)`** bar/bin.

## Frontend
- Wire **metadata-key `DistributionSource`s** into the collection layout
  (`routes/.../[collection_id]/+layout.svelte`, alongside the existing annotation-type
  sources): categorical key → bar source, numerical key → histogram source.
- Add a **histogram render path** in/next to `BarChart` (`BarChart/buildEchartsOption.ts`)
  — ECharts already supports grouped bars and line series.
- Add a **"compare tags" multi-select** to `DistributionConfigDialog`; on selection,
  fan the Issue-0 endpoint across the chosen tags (one call per tag's filter) and render
  one series per tag using the existing tag colors.
- Add the count/percentage toggle to the panel header/config.
- Reuse existing top-N, orientation toggle, and expand dialog.

## Backend
- None beyond Issue 0 (endpoint takes a `filter`; call once per tag).

## Acceptance
- Selecting a metadata key renders the correct chart type.
- Selecting 2–4 tags overlays comparable series (normalized by default, toggle to counts).
- Numerical histogram shares a global x-axis across compared tags.
- `(none)` appears when the key is missing for some samples.
