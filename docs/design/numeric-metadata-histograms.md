# Design doc: numeric metadata histograms (PR #1638)

Review notes for [LIG-9587](https://linear.app/lightly/issue/LIG-9587/frontend-numeric-metadata-histogram-2-sp)
and [LIG-10177](https://linear.app/lightly/issue/LIG-10177/backend-filter-aware-metadata-histogram-endpoint).
Rather than walking the code, this documents the **issues encountered along the
way and how each was resolved** — the code is the consequence. Each issue is
numbered so it can be referenced in review comments.

## What ships

The Dataset Distribution panel now charts numeric metadata as interactive
histograms next to the class-label distributions: pick **Distribution →
Metadata → key**, read the shape off numeric axes, click or drag across bars to
narrow the grid's metadata filter to that value range (re-select to reset), and
watch the counts track every other active filter. Demo data:
`make start-e2e-distribution` (env toggles `ADD_CLASSIFICATIONS`,
`ADD_OBJECT_DETECTIONS`, `ADD_SEGMENTATIONS`, `ADD_METADATA`).

## Issues and how they were resolved

### 1. The ticket depended on a component that never existed

LIG-9587 said "reuse the `Histogram` component from LIG-9575" — but LIG-9575
(chart infrastructure) was canceled; only the categorical `BarChart` existed,
and it is a poor fit for histograms (fixed 28px bars, scrolling, category axis).
**Resolution:** built a dedicated `Histogram` component on the same ECharts
stack `BarChart` established, so theming/tooltips come for free and no new
charting dependency was introduced.

### 2. One acceptance criterion was impossible against the existing API

"Chart updates live when active filters change" could not be met:
`GET /metadata/info` computes bins over the whole collection and accepts no
filter parameters. **Resolution:** flagged on the ticket instead of silently
dropping it, split into LIG-10177, and — after scope discussion — implemented
in this same PR (see issues 8–10).

### 3. Bars rendered with inconsistent hairline gaps

With bars drawn edge-to-edge, the chart showed uneven 0–1px seams between some
bars and not others. This went through three rounds:

- _Round 1 — sub-pixel widths._ The built-in bar series computes fractional
  per-bar widths; canvas antialiasing turns the fractional boundaries into
  seams. Stroking each bar with its own color closed the gaps…
- _Round 2 — alpha stacking._ …but the brand colors were semi-transparent, so
  the now-overlapping strokes stacked into visible _darker_ lines instead.
  Colors were made opaque.
- _Round 3 — residual seams._ Some boundaries still showed 1px gaps (fractional
  canvas transforms from device-pixel-ratio/zoom). Final fix: replace the bar
  series with a custom renderer that snaps every bin edge to integer pixels, so
  adjacent bins share the exact same edge coordinate — nothing left to
  antialias.

After the artifacts were gone, a **deliberate, uniform 1px gap** between bars
was added as a design choice — possible to guarantee only because edges are
integer-snapped.

### 4. The distribution was unreadable without hovering

The first version had no axes; values were only visible in tooltips.
**Resolution:** numeric axes (bin-edge values on x, counts on y) — but only in
the distribution panel. The component also supports an axis-less inline mode
(designed to sit above the filter sliders, where axis gutters would break the
bar↔slider alignment); that integration is intentionally **not wired up in this
PR** — the distribution panel is the single consumer.

### 5. Selecting one bar highlighted three

Clicking a bar highlighted it _and_ both neighbors. Cause: the highlight
treated a bin as selected when it merely _touched_ the range boundary, but bins
are half-open `[start, end)` — a shared edge is not an overlap. **Resolution:**
strict interior-overlap semantics; zero-width bins (constant-valued fields)
compare inclusively so the degenerate single-bin case still highlights.

### 6. The panel's "Source" dropdown conflated two different questions

Adding "Metadata" alongside "All types / Classification / Object detection /
Segmentation" mixed _what to distribute_ with _which subset of it_ in one flat
list. **Resolution:** two-level selection — first the distribution type (Class
labels / Metadata), then a contextual second dropdown (annotation type /
metadata key) — mapped onto the panel's existing source→group model. The panel
was also de-specialized ("Class distribution" → "Distribution") since classes
are now just one representation.

### 7. Filtering from the chart: click, then drag, then reversibility

Reading a distribution naturally leads to "show me only these bars". Landed in
three steps: click a bar → filter narrows to its interval; press-drag-release →
filter spans the selected bars (with live preview while dragging, working over
gaps and short bars, in both directions, clamped at chart edges); re-selecting
the exact current range → filter resets to full bounds, so every chart action
is undoable from the chart itself. A plain click is treated as a zero-width
drag, so one interaction model covers everything.

### 8. Filtered counts would have made the axis jump

Recomputing histograms over the filtered subset naively also _recomputes the
bin edges_, so the x-axis rescales on every filter change and bars appear to
move rather than shrink. **Resolution:** bin edges are always computed over the
full, unfiltered domain of each key; only the counts respect the filters. The
axis stays put; bars shrink in place.

### 9. A field filtered by itself shows a useless histogram

If a key's own range filter applies to its own histogram, narrowing the range
collapses the chart to exactly the selected bars — you lose the context of what
you are cutting off. **Resolution:** faceted-search semantics: each key's own
metadata filter is excluded from its histogram (its selection is communicated
via highlight instead), while every _other_ filter — tags, classes, dimensions,
other metadata keys — applies. This matches how FiftyOne and classic faceted
search behave.

### 10. The filter model is image-shaped

Dimension filters (width/height) reference the image table, so the histogram
endpoint applies filters through an image sample-ids subquery and is
image-scoped — same limitation as the distribution panel itself. Video/frame
collections need a follow-up variant.

### 11. Constant-valued fields looked broken

A field where every sample has the same value (`sensor_gain: 1.0`) produces a
degenerate zero-width bin and a min==max slider, and initially appeared as "no
histogram at all". Investigation showed the chart handled the case correctly
(verified by headless rendering); the missing chart had a different cause
(issue 12). The degenerate case is now explicitly handled end-to-end: single
full-width bar, inclusive highlight, filtered count.

### 12. Working-tree files kept reverting during the session

Twice, freshly written filter-panel integration files reverted to their
original content within minutes (stale editor buffers or a stray
`git restore`). Worth knowing for review: it is why the inline above-slider
histogram is absent from this PR — after the second revert we decided to keep
this PR panel-only (see issue 4) rather than fight the tooling.

### 13. The histogram lacked the categorical plot's config affordances

The class-labels chart has expand / configure / orientation controls; the
histogram initially had none, and 20 fixed bins washed out heavily skewed
fields. **Resolution:** the histogram header gained a bin-count preset select
(10/20/50/100 — bins are computed server-side, so the endpoint took a
`bin_count` parameter and the query refetches on change) and an expand button
opening a full-size dialog with the same axes, highlight, and drag-to-filter
interactions. The horizontal/vertical toggle was **deliberately not** carried
over: orientation earns its place on the categorical chart because class labels
need gutter space, but a histogram has no per-bar labels — its x-axis _is_ the
value domain, and rotating it would complicate the pixel-snapped renderer and
drag-select mapping for little gain.

### 14. Bin boundaries vs. inclusive range filters

A histogram bin is `[start, end)`, but the range filter created from a bar
selection is inclusive on both ends (`>= start`, `<= end`), so values sitting
exactly on the upper edge — which visually belong to the _next_ bar — are
included. Fixing this exactly would require an exclusive `<` operator in the
filter builder. Accepted for now; documented as a known limitation.

## Other known limitations

- Bin count is preset-based (10/20/50/100); no equal-count ("auto") binning
  for heavily skewed fields.
- Mouse-only drag selection (no touch).
- Backend tests (`tests/metadata/test_get_metadata_histograms.py`) were written
  but could not be executed in the implementation sandbox — please run
  `make test-ci` before merging.
