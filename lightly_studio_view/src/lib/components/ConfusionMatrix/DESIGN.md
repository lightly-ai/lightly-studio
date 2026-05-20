# ConfusionMatrix — design spec

Status: draft for LIG-9596. Reviewed with @kondrat; pending frontend reviewer sign-off.

This doc replaces a Figma file. It captures the visual and behavioural intent
of `<ConfusionMatrix>` so the design survives outside of any one branch.

## Visual reference

Two artefacts pin the visual intent:

1. The prototype on `origin/jonas-model-eval-cvpr-proto` at
   `lightly_studio_view/src/lib/components/ConfusionMatrix/ConfusionMatrix.svelte`
   is the live implementation reference.
2. `ConfusionMatrix.design.svg` next to this doc is a static design mockup
   reproducing the proto's visual language at a 1440 × 940 artboard size,
   with named layers (`id` on every `<g>` and `<rect>`). It can be opened in
   any browser, or dragged into a Figma frame for an editable starting point
   — Figma preserves the `id`s as layer names so the import lands as
   `confusion-matrix › header / threshold-controls / cells / row-car / cell-car-car`
   in the layers panel.

If you also want a 30-class screenshot for the design file, attach
`reference-proto.png` (a screenshot of the live proto on a COCO eval run)
to this folder.

## Library

ECharts v6 (`echarts@^6.0.0`), heatmap series with `visualMap`. Picked because:

- It handles 30+ classes with pan/zoom out of the box (`dataZoom inside`).
- Two heatmap series + per-series `visualMap` is the cleanest way to encode
  TP vs FP/FN with different color ramps without manual cell coloring.
- Canvas renderer keeps frame rate high when the user drags the threshold
  sliders and the matrix recomputes.

### Bundle-size constraint

ECharts is ~1MB minified — over the 500KB chunk limit in
`ai_guidelines/frontend.md`. Two mitigations, both applied:

1. **Modular imports only.** Never `import * as echarts from 'echarts'`. Use
   tree-shakeable subpath imports:

   ```ts
   import * as echarts from 'echarts/core';
   import { HeatmapChart } from 'echarts/charts';
   import {
       TooltipComponent,
       VisualMapComponent,
       GridComponent,
       DataZoomInsideComponent,
   } from 'echarts/components';
   import { CanvasRenderer } from 'echarts/renderers';

   echarts.use([
       HeatmapChart,
       TooltipComponent,
       VisualMapComponent,
       GridComponent,
       DataZoomInsideComponent,
       CanvasRenderer,
   ]);
   ```

2. **Dynamic import at the eval-run page.** The eval-run page should
   `await import('$lib/components/ConfusionMatrix')` so the chart only loads
   on the page that uses it.

## Data contract

Mirrors the shipped Pydantic model in
`lightly_studio/src/lightly_studio/models/evaluation_confusion_matrix.py` (see
LIG-9514). The component does not depend on the raw endpoint client; instead
it takes a normalized prop so storybook fixtures, the real client, and any
future client-side filter (LIG-9596 threshold sliders) can all share the same
shape.

```ts
// Endpoint shape, snake_case to match the generated API client.
export interface ConfusionMatrix {
    row_labels: string[];  // GT axis; trailing "(no ground truth)" unless empty
    col_labels: string[];  // Pred axis; trailing "(no prediction)" unless empty
    counts: number[][];    // counts[i][j] = row_labels[i] (GT) x col_labels[j] (pred)
}

export const NO_GROUND_TRUTH_ROW_LABEL = '(no ground truth)';
export const NO_PREDICTION_COL_LABEL = '(no prediction)';

// Prototype-only: raw per-pairing data drives the client-side threshold story.
// Not in the shipped endpoint — see "Open question: thresholds" below.
export interface AnnotationPairing {
    gt_label: string | null;   // null => false positive bucket
    pred_label: string | null; // null => false negative bucket
    confidence: number | null; // 0..1; null when there is no prediction
    iou: number | null;        // 0..1; null when there is no overlap
}

export interface Thresholds {
    confidence: number; // 0..1
    iou: number;        // 0..1
}

export interface ConfusionMatrixProps {
    data:
        | { kind: 'matrix'; matrix: ConfusionMatrix }
        | { kind: 'pairings'; pairings: AnnotationPairing[]; thresholds: Thresholds };
    normalize?: 'none' | 'row' | 'col'; // default 'row'
    showPercentInTooltip?: boolean;     // default true
}
```

## Axes

- **Rows = ground truth, columns = predictions.** Matches the backend model
  and the standard OD confusion-matrix convention. Diagonal cells are TPs.
- **Unified label set on both axes.** The component computes
  `allLabels = sortedUnique([...row_labels, ...col_labels])` and uses it for
  both x and y. This guarantees the diagonal aligns even when a label only
  appears on one side (e.g. a class with predictions but no GT).
- **Sentinel labels** (`(no ground truth)`, `(no prediction)`) are always
  pushed to the end of the sort regardless of alphabetical order. They render
  italicised in muted text so users can tell at a glance that those rows/cols
  aren't real classes.
- **Y-axis reversed** so the first label sits at the top — standard reading
  order, opposite of ECharts' default for category axes.
- **Axis labels rotated 45° on the x-axis** so 20+ classes don't overlap.

## Color encoding

Two heatmap series with independent `visualMap`s — the trick lifted from
Jonas's prototype:

| Series | Cells                                        | Color ramp                                       |
| ------ | -------------------------------------------- | ------------------------------------------------ |
| TP     | `gt_label === pred_label`, both non-null     | green: `rgba(34, 197, 94, 0.15)` → `0.95`        |
| FP/FN  | everything else (off-diagonal, including FP row and FN col) | red: `rgba(239, 68, 68, 0.15)` → `0.95`          |

- Color intensity scales with **absolute count**, capped at the matrix max,
  per series. (Using `count` rather than row-% means a single dominant class
  doesn't wash out everything else — matches the proto.)
- No explicit diagonal border is needed; the green vs red split makes the
  diagonal obvious without decoration.
- Zero-count cells get no fill — the heatmap simply skips them.

## Cell content

- Default: no inline label; the count is in the tooltip only. Keeps the
  matrix readable at high class counts.
- Tooltip on hover: `GT: <label>` / `Pred: <label>` / `Count: <n>`. If
  `normalize === 'row'`, append `Row %: <n / row_sum>`; same for col.

## Sizing

- Container height: `Math.max(320, allLabels.length * 48 + 180)` px — matches
  the proto. Each label gets ~48px of axis space (enough for rotated text);
  +180px is fixed chrome (grid margins, axis labels, x-axis rotation).
- Width fills the parent. `ResizeObserver` triggers `chart.resize()` on
  container changes.

## Interactivity

- **Pan and zoom** on both axes via `dataZoom: [{ type: 'inside', xAxisIndex: 0 }, { type: 'inside', yAxisIndex: 0 }]`. Scroll to zoom, drag to pan.
- **Tooltip** as above.
- **Emphasis** (hover state): subtle shadow blur on the hovered cell.
- **Threshold sliders** (when `data.kind === 'pairings'`): confidence and IoU
  sliders in a strip above the matrix. Changing either reruns
  `buildConfusionMatrix(pairings, thresholds)` and triggers `chart.setOption`
  with the new data. Default thresholds: **confidence 0.25, IoU 0.50**.

## States

| State                                | Render                                                                            |
| ------------------------------------ | --------------------------------------------------------------------------------- |
| Loaded with data                     | Heatmap as above.                                                                 |
| Empty (`row_labels.length === 0`)    | "No pairing metrics for this run." muted-text placeholder, no chart instance.     |
| Single class                         | 1×1 (well, 2×2 with the sentinels) matrix; tooltip still works.                   |
| No predictions above threshold       | Every prediction becomes a FN; the FP row is empty, the FN col is hot.            |
| No ground truth                      | Every prediction becomes a FP; the FP row is hot, the FN col is empty.            |

The last two are reachable only via the `kind: 'pairings'` story (threshold
sliders); they can't happen with the shipped endpoint as-is.

## Copy

- Component title in the eval-page card: **Confusion matrix**.
- Empty placeholder: **No pairing metrics for this run.**
- Sentinel labels (verbatim from backend): **(no ground truth)** /
  **(no prediction)**.
- Sentence case throughout. No "Ground Truth", no "GT".

## Open question: thresholds

The shipped endpoint (LIG-9514, PR #1166) **does not accept thresholds** —
thresholds are baked in when the per-pairing metric rows are persisted. The
client-side slider story in this prototype intentionally uses a richer
per-pairing fixture shape so we can prototype the UX, but production wiring
needs one of:

1. A new endpoint that takes thresholds and recomputes (parameterise
   LIG-9514).
2. A second endpoint that returns the raw pairings and we filter client-side
   (matches the prototype exactly).
3. Drop live thresholds; show the run's configured thresholds as read-only
   metadata.

Decision deferred to LIG-9597 / LIG-9599 (the integration tickets).

## Decisions log

- 2026-05-20: data shape = snake_case to match the generated API client
  (kondrat).
- 2026-05-20: visual language adopted from
  `origin/jonas-model-eval-cvpr-proto` instead of building a fresh design
  (kondrat).
- 2026-05-20: threshold sliders implemented as client-side filter in the
  prototype; production wiring TBD (kondrat).

## Files

- `ConfusionMatrix.svelte` — component (ECharts wrapper).
- `ConfusionMatrix.stories.svelte` — Storybook stories per state.
- `ConfusionMatrix.test.ts` — minimal smoke test (renders, calls `setOption`).
- `buildConfusionMatrix.ts` + `buildConfusionMatrix.test.ts` — pure helper
  that turns pairings + thresholds into a `ConfusionMatrix`. Unit-tested
  exhaustively.
- `fixtures.ts` — `small3Classes`, `large12Classes`, `empty`, `singleClass`,
  `noPredictionsAboveThreshold`, `noGroundTruth`.
- `types.ts` — types above.
- `index.ts` — barrel.
- `ConfusionMatrix.design.svg` — design mockup at artboard size, Figma-import
  ready (named layers via `id` attributes).
- `reference-proto.png` — optional: screenshot of Jonas's prototype on a
  larger eval run, attached manually.
