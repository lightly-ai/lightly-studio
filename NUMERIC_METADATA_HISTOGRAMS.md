# Numeric metadata histograms (PR #1638)

Implementation notes for review. Covers [LIG-9587](https://linear.app/lightly/issue/LIG-9587/frontend-numeric-metadata-histogram-2-sp)
(frontend numeric metadata histogram) and [LIG-10177](https://linear.app/lightly/issue/LIG-10177/backend-filter-aware-metadata-histogram-endpoint)
(filter-aware histogram endpoint), which was pulled into this branch after discussion.
Comment on any section — each design decision is numbered so it can be referenced directly.

## What this PR delivers

The Dataset Distribution panel is now generic: "Class labels" is one distribution
type among others, and numeric metadata is the second. Selecting **Distribution →
Metadata** and a **Metadata key** renders that field's value distribution as a
histogram with numeric axes. The histogram is interactive: clicking a bar narrows
the metadata filter for that key to the bar's value interval, press-drag-release
selects a range of bars, and re-selecting the exact current range resets the
filter to the full bounds. The active filter range is highlighted (bars outside
it are dimmed), and the bin counts themselves track every *other* active filter —
tags, class labels, dimensions, other metadata keys — refetching whenever the
view changes.

User-visible features:

- `Histogram` chart component (ECharts) with numeric x-axis (bin-edge values) and count y-axis
- Distribution panel: two-level selection — distribution type (Class labels / Metadata), then a contextual second dropdown (annotation type / metadata key); both selects equal width, first populated source auto-selected
- Bin tooltips with the exact value interval, count, and percentage
- Click / drag-to-select bars → applies the metadata range filter to the grid; re-select → reset
- Filter-aware counts with a stable x-axis (see decisions 8–10)
- `make start-e2e-distribution` seeds a demo dataset; env toggles `ADD_CLASSIFICATIONS`, `ADD_OBJECT_DETECTIONS`, `ADD_SEGMENTATIONS`, `ADD_METADATA` (all default true) control the content
- Storybook stories for the Histogram (shapes, selection, axes) and the panel (numeric metadata source)

## How it is built

### Frontend

- `lib/components/Histogram/` — presentational chart.
  - `buildHistogramOption.ts` builds the ECharts option: a **custom series** draws
    each bin as a pixel-snapped rect; the x-axis is a *value* axis over bin
    indices (bin *i* spans `[i, i+1]`), so axis ticks land exactly on bin edges
    and tick labels map back to data values by linear interpolation.
  - `Histogram.svelte` owns the ECharts instance and the drag-selection state.
    Selection uses zrender canvas events (`mousedown`/`mousemove`) plus a window
    `mouseup` listener, mapping pixels to bins via `convertFromPixel`. While
    dragging, the prospective range is previewed through the same highlight used
    for the committed selection.
- `lib/hooks/useNumericMetadataDistribution/` — TanStack query against the new
  endpoint, keyed on `(collection, filter)` so any filter change refetches;
  `placeholderData` keeps the previous bars during refetch. Mirrors the
  `useImageAnnotationCounts` pattern.
- `DatasetDistributionPanel` — `DistributionSource`/`DistributionSourceGroup`
  gained optional `histogram` + `selectedRange` fields (mutually exclusive with
  categorical `data`). A group carrying bins renders the `Histogram` (axes on)
  instead of the `BarChart`, swaps the categorical header (sort / top-N /
  orientation) for a compact summary line ("12 400 samples · 20 bins · 0–255"),
  and emits `onHistogramRangeSelect(groupId, range)`.
- `+layout.svelte` — builds the two sources (class labels with annotation-type
  groups; metadata with per-key histogram groups), feeds the histogram query the
  same `ImageFilter` that drives the grid, and applies range selections via
  `updateMetadataValues` (with the re-select-to-reset toggle).

### Backend

- `POST /api/collections/{collection_id}/metadata/histograms`
  (`api/routes/api/metadata.py`), body `{ filters?: ImageFilter }` — the same
  filter model the samples/counts endpoints use — returning
  `dict[metadata_key, HistogramView]`.
- `resolvers/metadata_resolver/sample/get_metadata_info.py` —
  `get_metadata_histograms()` reuses the existing SQL bucketing
  (`floor/least/greatest`, 20 bins, works on DuckDB and PostgreSQL). Filters are
  applied as a `sample_id IN (subquery)` where the subquery is
  `select(ImageTable.sample_id) → join sample → filters.apply(...)`, because
  dimension filters reference `ImageTable`. `ImageFilter` is imported under
  `TYPE_CHECKING` only, to avoid an import cycle through
  `sample_filter → metadata_resolver`.
- OpenAPI client regenerated via the standard `openapi.json` → `@hey-api/openapi-ts`
  flow (no hand-edited generated files). `openapi.json` is gitignored; the next
  `make export-schema` regenerates it from the backend code.

## Design decisions

1. **ECharts, not a hand-rolled SVG or d3.** ECharts is already a dependency
   (`BarChart`), so the histogram reuses the established chart stack, theming
   constants, and tooltip machinery at no bundle cost. (The `Histogram` component
   originally planned in LIG-9575 was canceled; this PR effectively supersedes it
   for the histogram half.)
2. **Custom series with pixel-snapped rects.** The built-in bar series computes
   fractional bar widths; at 0% gap, canvas antialiasing turns those into uneven
   hairline seams. `renderHistogramBin` rounds both edges of every bin to integer
   pixels, so adjacent bins share the exact same edge coordinate at any chart
   width.
3. **Deliberate uniform 1px gap between bars** (`BIN_GAP_PX`), carved out of each
   bin's right edge after snapping — visually separates bins and is exactly 1px
   everywhere. Bars never collapse below 1px width.
4. **Opaque bar colors** (`#3bd99f` accent / `#4b5563` dimmed). Any alpha would
   stack into visible darker seams wherever rects touch or overlap.
5. **Strict interior-overlap highlight semantics.** Bins are half-open
   `[start, end)`; a selection that merely touches a bin's edge does not select
   it, so selecting exactly one bar highlights exactly one bar (not its
   neighbors). Zero-width bins (constant-valued fields) compare inclusively.
6. **Selection = press-drag-release on the canvas layer.** zrender events fire
   anywhere on the canvas (also over gaps and short bars), and `convertFromPixel`
   maps pixels to bins; a plain click is a zero-width drag, so one callback
   (`onRangeSelect`) covers both. Re-selecting the current range resets the
   filter — clicking is therefore always reversible.
7. **Two-level selection model in the panel.** The earlier flat source list mixed
   two dimensions (what to distribute × which subset). Now level 1 is the
   distribution type (Class labels / Metadata) and level 2 is contextual
   (annotation type / metadata key), mapped onto the panel's existing
   source→group model — no new panel machinery.
8. **Stable bin edges under filtering.** Bin edges always span the full
   (unfiltered) domain of each key; only counts change with filters. The x-axis
   never jumps while the user adjusts filters, and bars shrink in place.
9. **Faceted-search filter semantics.** Each key's *own* metadata filter is
   excluded from its histogram (server-side): the full shape of the field being
   adjusted stays visible — its selection is shown via highlight instead — while
   every other filter applies. This mirrors e.g. FiftyOne's per-view histograms
   and classic faceted search.
10. **Filters applied via a sample-ids subquery**, not by joining filters into
    the bucketing query directly — keeps the metadata SQL untouched and lets the
    full `ImageFilter` (tags, annotations, dimensions, query expressions,
    confusion cells) apply uniformly.
11. **Histograms query only while the panel is open**, and the previous response
    is kept as placeholder data during refetches, so filter changes don't blank
    the chart and closed panels cost nothing.
12. **The inline filter-panel variant (histogram above each range slider) is
    currently not wired up.** The `Histogram` component supports it (axis-less
    mode, slider-aligned edge-to-edge layout, live drag highlight), but the
    integration was deliberately left out of this PR; the distribution panel is
    the single consumer. Revisit as a follow-up if wanted.

## Testing

- `Histogram`: option-builder unit tests (colors, highlight semantics, tooltip,
  pixel snapping, 1px gap, degenerate single bin) and component tests
  (render/empty states, drag selection incl. right-to-left and edge clamping)
  with a mocked ECharts.
- `DatasetDistributionPanel`: histogram vs bar-chart rendering, summary line,
  categorical-controls suppression, range-select forwarding, default-source
  selection.
- Hook: response-mapping selector tests.
- Backend: `tests/metadata/test_get_metadata_histograms.py` — unfiltered totals,
  filtered counts with stable edges, own-key exclusion, constant fields,
  non-numeric keys skipped.

## Known limitations / follow-ups

- Histogram bin count is fixed at 20 (`_HISTOGRAM_BIN_COUNT`); no equal-count
  ("auto") binning for heavily skewed fields yet.
- The endpoint is image-scoped (dimension filters reference `ImageTable`), like
  the distribution panel itself; video/frame collections would need a variant.
- Values exactly on a shared bin edge belong to the upper bin, but a range
  filter `[edges[i], edges[i+1]]` is inclusive on both ends — a click can include
  boundary values that visually belong to the next bar. Exact half-open filter
  ops would need a `<` operator in `createMetadataFilters`.
- No drag-select on touch devices (mouse events only).
