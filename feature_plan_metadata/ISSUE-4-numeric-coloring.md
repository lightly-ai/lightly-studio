# Issue 4 — Numeric-metadata coloring of the embedding plot (ordered gradient)

**Depends on:** nothing (self-contained). **Blocks:** conceptually the "reuse color
coding" idea, but Issue 3 chose tag-only coloring, so no hard block. Build early — small.

## Goal
Make coloring the embedding plot by a **numeric** metadata field work (`float` currently
raises "unsupported type"; `integer` only range-buckets), using **buckets with a proper
ordered gradient** so the color is easy to interpret at a glance.

## Decisions
- **Bucketed, not continuous colorbar.** Use **quantile bins** (equal sample counts) so
  color contrast reflects the actual distribution. ~5–8 bins.
- **Ordered sequential ramp**, NOT the categorical OKLCH **hue wheel** (which would look
  like an unordered rainbow). Use a **single-hue OKLCH ramp** (fixed hue, lightness
  ~0.9→0.35 across bins) — perceptually monotonic and colorblind-safe. "Darker = higher."
- **Legend** shows **range labels** per bin (e.g. `0.10–0.42`) in gradient order.
- **Missing values:** points missing the numeric value are **dim gray**
  (`UNASSIGNED_COLOR`), never hidden.

## Backend (`embedding_coloring/metadata.py`)
- Support `float` (and reuse for `integer`): compute **quantile** bin edges, assign each
  point a bin id → the existing `color_categories:list<uint8>` channel.
- Add an **`ordered: true`** flag plus the **bin-edge / range labels** into the
  `color_legend` schema metadata (`embeddings2d.py` already writes `color_legend`).
- Emit a distinct id/label for the missing-value bucket.

## Frontend (`PlotPanel/plotColorUtils.ts`, `useArrowData.ts`, legend)
- Parse the `ordered` flag + range labels from the Arrow schema metadata.
- When `ordered`, generate bucket colors via a **sequential OKLCH lightness ramp** keyed
  by bin index instead of `oklchHueWheelColor`; render legend entries as ordered ranges.
- Map the missing-value bucket to `UNASSIGNED_COLOR` (gray).
- Nominal color-bys (annotation/tags/categorical metadata) keep the existing hue wheel.

## Acceptance
- Coloring by a `float` (and `integer`) metadata field renders an ordered gradient with
  range-labeled legend entries; higher values are visibly "further along" the ramp.
- Samples missing the value are gray.
- Categorical/annotation/tag coloring is unchanged (still hue wheel).
