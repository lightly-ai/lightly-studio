# STU-271 Display Polygon Annotations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Draw the real polygon outline and fill, instead of its bounding box, wherever the GUI shows annotations.

**Architecture:** The canvas renderer (grids) gets a third input, `PolygonInput`, next to masks and boxes. The worker and the main thread both draw it after masks and before boxes. The SVG renderer (detail view, video player) draws one `<path>` per polygon in a new `SampleAnnotationPolygon` component, which is also the click target.

**Tech Stack:** SvelteKit, Svelte 5, TypeScript, Canvas 2D / OffscreenCanvas worker, SVG, vitest.

**Spec:** `.experimental/superpowers/specs/2026-11-27-stu-271-display-polygon-annotations-design.md`

## Global Constraints

- Frontend only. The API already sends `polygon_details.polygons: Array<Array<[number, number]>>` in image pixels.
- No bounding box around polygons, on any surface. `showBoundingBoxesForSegmentation` does not apply to polygons.
- The label tag stays at the top-left corner of the polygon's bounding box (`polygon_details.x/y`).
- Fill rule `nonzero`. All parts of one polygon go into one path, filled once. Both renderers first give every part the same winding (Task 1), because opposite-winding parts cancel under `nonzero`.
- Stroke width 2 (same as boxes). Fill alpha 0.4 (same as SVG boxes).
- Load `frontend-guide` and `clean-code` before editing. Run only affected vitest files, never the full suite.
- Run every command from `lightly_studio_view` (after `nvm use`); all paths in commands are relative to it.
- Out of scope: drawing or editing polygons, backend changes, the selection rectangle of `SelectableSvgGroup` (it stays a box).

## Review Focus

1. "Show bounding boxes for segmentation" is on → polygons still have no box (canvas: Task 4; SVG: Task 5).
2. Detail view highlight `disabled` / `active` → polygon dims or clears its fill like a box does (Task 5).
3. Overlapping parts of one polygon, wound in opposite directions → no hole: parts are normalized to one winding and filled in one `fill('nonzero')` call (Tasks 1, 2, 5).
4. Coloring by source and custom label colors → polygon stroke on canvas uses the source/custom color (Task 3).
5. Clicking inside the polygon in the detail view selects the annotation, also when `showBoundingBox` is false (Task 5).

---

### Task 1: Polygon winding helper

**Files:**
- Create: `src/lib/utils/normalizePolygonWinding.ts`
- Test: `src/lib/utils/normalizePolygonWinding.test.ts`

**Interfaces:**
- Produces:
  ```ts
  export type PolygonPart = ReadonlyArray<readonly [number, number]>;
  export const normalizePolygonWinding: (parts: ReadonlyArray<PolygonPart>) => PolygonPart[];
  ```
  Returns each part with a non-negative signed (shoelace) area: parts with negative area are reversed, others are returned unchanged. Does not mutate its input.

- [ ] **Step 1: Write the failing tests**

```ts
it('reverses a part wound against the others', () => {
    const positive: PolygonPart = [[0, 0], [4, 0], [4, 4], [0, 4]];
    const negative: PolygonPart = [[2, 2], [2, 6], [6, 6], [6, 2]];
    expect(normalizePolygonWinding([positive, negative])).toEqual([
        positive,
        [[6, 2], [6, 6], [2, 6], [2, 2]]
    ]);
});
it('does not mutate the input', () => {
    const parts: PolygonPart[] = [[[0, 0], [0, 4], [4, 4]]];
    const copy = structuredClone(parts);
    normalizePolygonWinding(parts);
    expect(parts).toEqual(copy);
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx vitest run src/lib/utils/normalizePolygonWinding.test.ts`
Expected: FAIL, module not found.

- [ ] **Step 3: Implement `normalizePolygonWinding` in `src/lib/utils/normalizePolygonWinding.ts`**

Keep the signed-area computation a private function at the bottom of the file.

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx vitest run src/lib/utils/normalizePolygonWinding.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/lib/utils/normalizePolygonWinding.ts src/lib/utils/normalizePolygonWinding.test.ts
git commit -m "feat: add a helper that gives polygon parts the same winding"
```

---

### Task 2: Canvas polygon helpers

**Files:**
- Modify: `src/lib/workers/maskRendererUtils.ts`
- Test: `src/lib/workers/maskRendererUtils.test.ts`

**Interfaces:**
- Consumes: `PolygonPart`, `normalizePolygonWinding` from Task 1.
- Produces (exported from `maskRendererUtils.ts`):
  ```ts
  export interface PolygonInput {
      parts: PolygonPart[];
      strokeColor: [number, number, number, number];
      fillColor: [number, number, number, number];
  }
  export const transformPolygons: (geometry: RenderGeometry, polygons: PolygonInput[]) => PolygonInput[];
  export const drawPolygonsOnContext: (ctx: PolygonContext, polygons: PolygonInput[], stroke?: number) => void; // stroke defaults to 2
  ```
  `PolygonContext` is a `Pick<CanvasRenderingContext2D | OffscreenCanvasRenderingContext2D, ...>` of `save restore lineWidth strokeStyle fillStyle beginPath moveTo lineTo closePath fill stroke`, like `BoxContext`.

- [ ] **Step 1: Write the failing tests**

```ts
it('maps polygon vertices into output space', () => {
    // contain 200x100 into 200x200: scale 1, offsetY 50
    const [polygon] = transformPolygons(geometry({ sourceWidth: 200, sourceHeight: 100 }), [
        { parts: [[[0, 0], [10, 0], [10, 20]]], strokeColor: [1, 2, 3, 255], fillColor: [1, 2, 3, 102] }
    ]);
    expect(polygon.parts).toEqual([[[0, 50], [10, 50], [10, 70]]]);
    expect(polygon.strokeColor).toEqual([1, 2, 3, 255]);
});

it('applies the source crop when mapping polygon vertices', () => {
    // crop {x:10,y:10,w:50,h:50} into 200x200: scale 4, offset -40
    const [polygon] = transformPolygons(
        geometry({ sourceCrop: { x: 10, y: 10, width: 50, height: 50 } }),
        [{ parts: [[[10, 10], [20, 10], [20, 20]]], strokeColor: [0, 0, 0, 255], fillColor: [0, 0, 0, 0] }]
    );
    expect(polygon.parts).toEqual([[[0, 0], [40, 0], [40, 40]]]);
});

it('fills all parts of a polygon in one nonzero path, then strokes it', () => {
    const ctx = createPolygonContext(); // vi.fn() for every PolygonContext method
    drawPolygonsOnContext(ctx, [
        {
            parts: [[[0, 0], [4, 0], [4, 4]], [[2, 2], [6, 2], [6, 6]]],
            strokeColor: [255, 0, 0, 255],
            fillColor: [255, 0, 0, 102]
        }
    ]);
    expect(ctx.beginPath).toHaveBeenCalledTimes(1);
    expect(ctx.moveTo.mock.calls).toEqual([[0, 0], [2, 2]]);
    expect(ctx.lineTo.mock.calls).toEqual([[4, 0], [4, 4], [6, 2], [6, 6]]);
    expect(ctx.closePath).toHaveBeenCalledTimes(2);
    expect(ctx.fill).toHaveBeenCalledExactlyOnceWith('nonzero');
    expect(ctx.stroke).toHaveBeenCalledTimes(1);
    expect(ctx.lineWidth).toBe(2);
    // fill happens before stroke
    expect(ctx.fill.mock.invocationCallOrder[0]).toBeLessThan(ctx.stroke.mock.invocationCallOrder[0]);
});

it('draws parts of opposite winding in the same direction', () => {
    const ctx = createPolygonContext();
    drawPolygonsOnContext(ctx, [
        {
            parts: [[[0, 0], [4, 0], [4, 4], [0, 4]], [[2, 2], [2, 6], [6, 6], [6, 2]]],
            strokeColor: [255, 0, 0, 255],
            fillColor: [255, 0, 0, 102]
        }
    ]);
    expect(ctx.moveTo.mock.calls).toEqual([[0, 0], [6, 2]]);
});

it('draws nothing for an empty polygon list', () => {
    const ctx = createPolygonContext();
    drawPolygonsOnContext(ctx, []);
    expect(ctx.save).not.toHaveBeenCalled();
});
```

To check the style strings, record `fillStyle`/`strokeStyle` at the time of the `fill`/`stroke` call in the mock, and expect `rgbaFromBytes(fillColor)` / `rgbaFromBytes(strokeColor)`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx vitest run src/lib/workers/maskRendererUtils.test.ts`
Expected: FAIL, `transformPolygons` / `drawPolygonsOnContext` not exported.

- [ ] **Step 3: Implement the types and both functions in `maskRendererUtils.ts`**

`transformPolygons` maps each vertex with `getRenderTransform`: `[x * scale + offsetX, y * scale + offsetY]`. No clipping: the canvas clips to its own bounds, and outside the crop the grid tile shows the image anyway. `drawPolygonsOnContext` mirrors `drawBoxesOnContext` (early return, `save`/`restore`, `lineWidth = stroke`), with one `beginPath` per polygon, `moveTo` + `lineTo` + `closePath` per part of `normalizePolygonWinding(polygon.parts)`, then `fill('nonzero')` and `stroke()`. Skip parts with fewer than 3 vertices.

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx vitest run src/lib/workers/maskRendererUtils.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/lib/workers/maskRendererUtils.ts src/lib/workers/maskRendererUtils.test.ts
git commit -m "feat: add canvas helpers to draw polygons"
```

---

### Task 3: Polygons in the worker and `AnnotationCanvas`

**Files:**
- Modify: `src/lib/workers/maskRenderer.worker.ts`
- Modify: `src/lib/workers/maskRenderer.testFixtures.ts` (add `polygons: []` to `createWorkerRenderMessage`)
- Modify: `src/lib/components/AnnotationCanvas/AnnotationCanvas.svelte`
- Test: `src/lib/workers/maskRenderer.worker.test.ts`, `src/lib/components/AnnotationCanvas/AnnotationCanvas.test.ts`

**Interfaces:**
- Consumes: `PolygonInput`, `transformPolygons`, `drawPolygonsOnContext` from Task 2.
- Produces:
  - Worker `RenderMessage` gains `polygons: PolygonInput[]`; the fallback `'image'` message gains `polygons: PolygonInput[]` (already transformed to output space).
  - `AnnotationCanvas` accepts a third annotation variant:
    ```ts
    interface PolygonAnnotation {
        annotation_type: 'polygon';
        annotation_label_name: string;
        polygons: Array<Array<[number, number]>>;
        segmentation_mask?: undefined;
        object_detection_details?: undefined;
        color?: string;
        opacity?: number;
        sourceName?: string;
    }
    ```

- [ ] **Step 1: Write the failing tests**

Worker test (extend the existing context mock with the `PolygonContext` methods):
- `'draws polygons after masks on the worker-owned canvas'`: send `init`, then `createWorkerRenderMessage({ polygons: [{ parts: [[[0, 0], [16, 0], [16, 8]]], strokeColor: [255, 0, 0, 255], fillColor: [255, 0, 0, 102] }] })`. Source 16×8 → output 8×4 is scale 0.5, so expect `moveTo(0, 0)`, `lineTo(8, 0)`, `lineTo(8, 4)`, and `putImageData` called before `fill`.
- `'posts transformed polygons in the fallback image message'`: no `init`; spy on `postMessage`; expect the message to contain `polygons: [expect.objectContaining({ parts: [[[0, 0], [8, 0], [8, 4]]] })]`.

`AnnotationCanvas` test (add the polygon methods to the existing canvas context mock):
- `'draws a polygon on the main-thread canvas when there are no masks'`: source 100×100, output 200×200, one `{ annotation_type: 'polygon', annotation_label_name: 'car', polygons: [[[10, 10], [50, 10], [50, 40]]] }`. Expect no worker (`MockWorker.instances` length 0), `moveTo(20, 20)`, `lineTo(100, 20)`, `lineTo(100, 80)`, `fill('nonzero')`, and no `strokeRect`.
- `'colors a polygon stroke by its source name'`: same polygon with `sourceName: 'Predictions'`; the `strokeStyle` recorded at `stroke()` is the parsed `getColorBySource('Predictions', 1)` color (follow the existing `'colors an annotation by its source name when set'` test for how colors are parsed in the mock).
- `'sends polygons to the worker when masks are present'`: one mask plus one polygon; the posted `render` message has `polygons` with one entry whose `parts` equal the input vertices (source space).

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx vitest run src/lib/workers/maskRenderer.worker.test.ts src/lib/components/AnnotationCanvas/AnnotationCanvas.test.ts`
Expected: the new tests FAIL; existing tests still pass.

- [ ] **Step 3: Implement**

- Worker `handleRender`: `transformPolygons(geometry, polygons)`. On the offscreen path draw in the order `putImageData` → `drawPolygonsOnContext` → `drawBoxesOnContext`. On the fallback path, add `polygons` to the posted message.
- `AnnotationCanvas.buildRenderPayload` returns `{ masks, boxes, polygons }`. For a polygon annotation push `{ parts, strokeColor: resolveAnnotationColor(annotation, 1, maps), fillColor: resolveAnnotationColor(annotation, POLYGON_FILL_ALPHA, maps) }` with `const POLYGON_FILL_ALPHA = 0.4`. Copy `parts` to plain arrays (`part.map(([x, y]) => [x, y])`) so `postMessage` never gets reactive proxies, like `toCloneableRLE`.
- Main-thread path (`!workerReady && masks.length === 0`): return early only if there are no boxes and no polygons; draw polygons, then boxes.
- `handleWorkerMessage`: read `polygons = []` from the message and draw them before boxes.

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx vitest run src/lib/workers src/lib/components/AnnotationCanvas`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/lib/workers src/lib/components/AnnotationCanvas
git commit -m "feat: draw polygons in the annotation canvas"
```

---

### Task 4: Polygons in the image, video frame and annotation crop grids

**Files:**
- Modify: `src/lib/components/SampleAnnotations/index.svelte` (used by the image grid and the video frame grid)
- Modify: `src/lib/components/AnnotationsGrid/AnnotationItem/AnnotationItem.svelte`
- Modify: `src/lib/components/AnnotationsGrid/AnnotationItem/AnnotationCanvas.mock.svelte` (add `annotation_type?: string` and `polygons?: Array<Array<[number, number]>>` to its `CanvasAnnotation` interface, then expose `data-annotation-type` and `data-polygons={JSON.stringify(annotations[0]?.polygons)}`)
- Test: `src/lib/components/SampleAnnotations/index.test.ts`, `src/lib/components/AnnotationsGrid/AnnotationItem/AnnotationItem.test.ts`

**Interfaces:**
- Consumes: the `PolygonAnnotation` variant of `AnnotationCanvas` from Task 3.

- [ ] **Step 1: Replace the polygon box tests with outline tests**

`SampleAnnotations/index.test.ts`: add `beginPath moveTo lineTo closePath fill stroke` as `ReturnType<typeof vi.fn>` to the `Mock2dContext` type (around line 95) and as `vi.fn()` to the `mockContext` initializer. Replace `'draws the box of a polygon annotation'` with `'draws the outline of a polygon annotation without a box'`: same sample, call `setShowBoundingBoxesForSegmentation(true)` first; `await waitFor` → `moveTo(5, 6)`, `lineTo(12, 6)`, `lineTo(12, 14)` were called and `strokeRect` was not.

`AnnotationItem.test.ts`: replace `'shows the box of a polygon annotation'` with `'draws the polygon on the canvas and hides its box'`: same annotation, `showLabel: true`. Expect the mock canvas has `data-annotation-type="polygon"` and `data-polygons` equal to `JSON.stringify(annotation.polygon_details.polygons)`; `annotation-box` has `borderColor: 'transparent'` and the same `width: '180px', height: '80px'` as before; the text `car` is shown.

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx vitest run src/lib/components/SampleAnnotations/index.test.ts src/lib/components/AnnotationsGrid/AnnotationItem/AnnotationItem.test.ts`
Expected: the two new tests FAIL.

- [ ] **Step 3: Implement**

- `SampleAnnotations.mapToCanvasAnnotation`: a polygon maps to `{ annotation_type: 'polygon', annotation_label_name, polygons: annotation.polygon_details.polygons }`, never with a box. Remove the "does not draw polygon outlines yet" comment.
- `AnnotationItem`: add `isPolygon = $derived(!!annotation.polygon_details)`. Render `AnnotationCanvas` when `isRLESegmentation || isPolygon`; for a polygon pass `{ annotation_type: 'polygon', annotation_label_name: labelName, polygons }` with no `color`/`opacity`, so the canvas resolves the label and custom color like it does in the image grid. Make the `annotation-box` border and background transparent for polygons as for masks (the label stays). Keep the component readable: compute the canvas annotation in one `$derived`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx vitest run src/lib/components/SampleAnnotations src/lib/components/AnnotationsGrid`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/lib/components/SampleAnnotations src/lib/components/AnnotationsGrid
git commit -m "feat: show polygon outlines in the grids"
```

---

### Task 5: Polygons in the detail view and video player (SVG)

Depends only on Task 1; independent of Tasks 2–4.

**Files:**
- Modify: `src/lib/components/SampleAnnotation/utils.ts`
- Create: `src/lib/components/SampleAnnotation/SampleAnnotationPolygon/SampleAnnotationPolygon.svelte`
- Modify: `src/lib/components/index.ts` (export it next to `SampleAnnotationBox`)
- Modify: `src/lib/components/SampleAnnotation/SampleAnnotation.svelte`
- Test: `src/lib/components/SampleAnnotation/utils.test.ts`, `src/lib/components/SampleAnnotation/SampleAnnotation.test.ts`

**Interfaces:**
- Consumes: `normalizePolygonWinding` from Task 1.
- Produces:
  - `export const polygonsToSvgPath = (polygons: Array<Array<[number, number]>>): string` in `utils.ts`.
  - `SampleAnnotationPolygon` props: `{ polygons: Array<Array<[number, number]>>; label: string; colorStroke: string; colorFill: string; opacity: number }`. Renders one `<path data-testid="annotation_polygon">` with `d={polygonsToSvgPath(polygons)}`, `fill-rule="nonzero"`, `stroke-width="2"`, `vector-effect="non-scaling-stroke"`, `fill={colorFill}`, `fill-opacity={opacity}`, `stroke={colorStroke}`, `pointer-events="all"`, `aria-label={label}` (match `SampleAnnotationBox`).

- [ ] **Step 1: Write the failing tests**

`utils.test.ts`:
```ts
it('converts each polygon part into a closed subpath', () => {
    expect(polygonsToSvgPath([[[1, 2], [11, 2], [11, 14]], [[20, 20], [30, 20], [30, 30]]])).toBe(
        'M1 2L11 2L11 14ZM20 20L30 20L30 30Z'
    );
});
it('skips parts with fewer than three vertices', () => {
    expect(polygonsToSvgPath([[[1, 2], [3, 4]]])).toBe('');
});
it('writes parts of opposite winding in the same direction', () => {
    expect(
        polygonsToSvgPath([[[0, 0], [4, 0], [4, 4], [0, 4]], [[2, 2], [2, 6], [6, 6], [6, 2]]])
    ).toBe('M0 0L4 0L4 4L0 4ZM6 2L6 6L2 6L2 2Z');
});
```

`SampleAnnotation.test.ts` — add a `createPolygonAnnotation()` factory (the polygon from the existing test) and replace `'shows the box of a polygon without resize handles in edit mode'` with:
- `'draws a polygon outline instead of a box, also in edit mode'`: props `isResizable: true`, `constraintBox`, `showBoundingBox: true`. Expect `annotation_polygon` has `d="M1 2L11 2L11 14Z"`; no `annotation_box`; no `resize-handle-nw`.
- `'draws the polygon when bounding boxes are hidden'`: `showBoundingBox: false` → `annotation_polygon` is present.
- `'shows the polygon label at the top-left of its box'`: `showLabel: true` → `svg-annotation-text` has text `car` (position comes from `boundingBox`, unchanged).
- `'dims a disabled polygon and clears the fill of an active one'`: render with `highlight: 'disabled'` → the path `stroke` equals `withAlpha(getColorByLabel('car', 1).color, 0.1)`; rerender with `highlight: 'active'` → `fill` equals `withAlpha(getColorByLabel('car', 0.4).color, 0)`.
- `'selects a polygon when the user clicks its outline area'`: render `SelectableSampleAnnotationHarness` with the polygon annotation (it passes `showBoundingBox={false}`), click `annotation_polygon`, expect `onSelect` called with `'polygon-1'`. The harness requires `prerenderedDataUrl`/`prerenderedHeight`; pass the same values as the mask test.

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx vitest run src/lib/components/SampleAnnotation`
Expected: new tests FAIL.

- [ ] **Step 3: Implement**

- `polygonsToSvgPath` in `utils.ts`, above the private helpers. It writes the parts of `normalizePolygonWinding(polygons)`.
- `SampleAnnotationPolygon.svelte` with the props above.
- `SampleAnnotation.svelte`: read `polygons = $derived(isPolygonAnnotation(annotation) ? annotation.polygon_details.polygons : undefined)`. When `polygons` is set, render `SampleAnnotationPolygon` with `colorStroke`, `colorFill`, `opacity={boundingBoxOpacity}`, and skip the `showBoundingBox` box block entirely. Leave `showAnnotationLabel` as is; it already shows the label for polygons. Remove the now-unneeded `!isPolygon` check on `ResizableRectangle` only if the polygon branch makes it unreachable; keep the TODO about read-only polygons.

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx vitest run src/lib/components/SampleAnnotation src/lib/components/VideoFrameAnnotation src/lib/components/VideoFrameAnnotationItem src/lib/components/SampleDetails/SampleDetailsAnnotation`
Expected: PASS

- [ ] **Step 5: Static checks and commit**

Run: `make static-checks`
Expected: no errors.

```bash
git add src/lib/components/SampleAnnotation src/lib/components/index.ts
git commit -m "feat: show polygon outlines in the detail view and video player"
```

---

### Task 6: Changelog

- [ ] Load the `changelog` skill and add one entry under Unreleased → Added in the repo-root `CHANGELOG.md` (`../CHANGELOG.md` from `lightly_studio_view`), e.g. "The GUI shows the outline and fill of polygon annotations instead of their bounding boxes." Commit with `docs: add changelog entry for polygon display`.
