# Adjustable 3D Cuboid Creation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users set a cuboid's size while creating it, by dragging in any view of the point cloud workspace.

**Architecture:** Pure TypeScript modules compute the draft box and fit it to points. A hook owns the pointer listeners and the draft step; a thin scene component renders the invisible plane and a preview box. The finished placement goes through the existing `onCreateCuboid` chain into `useCreateCuboidAnnotation`. No backend change.

**Tech Stack:** Svelte 5, Threlte (`@threlte/core`, `@threlte/extras`), three.js, vitest, Storybook.

**Spec:** `.experimental/superpowers/specs/2026-11-12-adjustable-cuboid-creation-design.md`

## Global Constraints

- All paths below are relative to `lightly_studio_view/`. `WS` = `src/lib/components/PointCloudLabelingWorkspace`.
- Load the `frontend-guide` skill before editing any `.ts` or `.svelte` file, `best-practices` for new modules, and `changelog` before editing `CHANGELOG.md`.
- A pointer-down and pointer-up less than **4 screen pixels** apart is a click; anything else is a drag.
- Every cuboid dimension is at least **0.1**.
- Drawn cuboids are world-aligned: `qx = qy = qz = 0`, `qw = 1`.
- A click creates exactly the box created today: a cube with edge `max(frameDiagonal * 0.02, 0.1)`, bottom face on the clicked point.
- Missing axis per view: top → Z, side → X, front → Y, perspective → Z.
- Run one test file: `npm run test:unit -- --run <path>`. Before each commit: `make static-checks`.
- Delivery is two pull requests: Tasks 1–5 (PR 1), Tasks 6–7 (PR 2, branched from PR 1).
- Commit messages end with `Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>`.

## Review Focus

1. **Reversed drag** (end corner left of or below the start corner): the box has positive sizes and the same centre as the forward drag. Test in Task 1.
2. **Accumulated point batches** (`batch.segments` set, buffers longer than `count * 3`): the fit reads every segment and only the first `count` points of each. Test in Task 2.
3. **Pointer lost mid-drag** (`pointercancel`, `lostpointercapture`, component unmount on tool change): the draft is discarded and nothing is created. Test in Task 4.
4. **Non-left button** (right or middle pointer-down on the plane): no draft starts, no cuboid is created, and a right-click during a draft does not open the browser context menu. Test in Task 4.
5. **Ray parallel to the draft plane** (`intersectPlane` returns `null`, possible in the 3D view near the horizon): the move is ignored and the preview keeps its last box. Test in Task 4.

---

## File Structure

| File | Responsibility |
|---|---|
| `WS/CuboidDraft/cuboidDraft.ts` (new) | Types, constants and pure geometry: click/drag test, rectangle from two corners, boxes from a rectangle, default quick-drop box |
| `WS/CuboidDraft/fitCuboidToPoints.ts` (new) | Extent of the missing axis from points inside a rectangle, with fallback |
| `WS/CuboidDraft/useCuboidDraft/useCuboidDraft.svelte.ts` (new) | Pointer and keyboard listeners, draft step, emits a `CuboidPlacement` |
| `WS/CuboidDraft/useCuboidDraft/CuboidDraftHarness.svelte` (new) | Test harness for the hook, like `CuboidFaceResizeHarness.svelte` |
| `WS/CuboidDraft/CuboidDraftTarget.svelte` (new) | Invisible plane mesh + preview; replaces `GroundPlaneClickTarget.svelte` |
| `WS/CuboidDraft/CuboidDraftPreview.svelte` (new) | Translucent preview box |
| `WS/CuboidDraft/index.ts` (new) | Re-exports `CuboidDraftTarget`, `CuboidBox`, `CuboidPlacement` |
| `WS/GroundPlane/GroundPlaneClickTarget/cuboidCreationPlane.ts` | Unchanged; still supplies the plane layout |
| `WS/GroundPlane/GroundPlaneClickTarget/GroundPlaneClickTarget.svelte` | Deleted in Task 5 |

The hook file is an addition to the spec's file table: it keeps the listeners testable with a harness, the pattern already used by `WS/CuboidLayer/CuboidFaceResize/useCuboidFaceResize/`.

---

## PR 1 — Drawing in orthographic views

### Task 1: Draft geometry (`cuboidDraft.ts`)

**Files:**
- Create: `WS/CuboidDraft/cuboidDraft.ts`
- Test: `WS/CuboidDraft/cuboidDraft.test.ts`

**Interfaces:**
- Consumes: `Vector3`, `Bounds3`, `CameraMode` from `WS/domain`.
- Produces:

```ts
export const DRAG_THRESHOLD_PX = 4;
export const MIN_CUBOID_EXTENT = 0.1;

export interface CuboidBox { center: Vector3; size: Vector3 }
export type CuboidPlacement =
    | { kind: 'drop'; position: Vector3 }
    | { kind: 'box'; box: CuboidBox };
export type Axis = 0 | 1 | 2;
export interface DraftRectangle {
    /** Axis not covered by the drag. */
    missingAxis: Axis;
    /** Coordinate of the draft plane on the missing axis. */
    planeCoordinate: number;
    /** Lower and upper corner; both carry planeCoordinate on the missing axis. */
    min: Vector3;
    max: Vector3;
}
export interface AxisExtent { min: number; max: number }
export interface ScreenPoint { x: number; y: number }

export function getMissingAxis(cameraMode: CameraMode): Axis;
export function isDrag(start: ScreenPoint, end: ScreenPoint): boolean;
export function getDraftRectangle(cameraMode: CameraMode, start: Vector3, end: Vector3): DraftRectangle;
export function getDraftBox(rectangle: DraftRectangle, extent?: AxisExtent): CuboidBox;
export function getDefaultCuboidBox(position: Vector3, bounds: Bounds3): CuboidBox;
```

`getDraftBox` without `extent` returns the flat preview box (missing-axis size `MIN_CUBOID_EXTENT`, centred on `planeCoordinate`). With `extent` it spans `extent.min..extent.max` on the missing axis. Every size is clamped to `MIN_CUBOID_EXTENT`; the centre does not move when a size is clamped.

- [ ] **Step 1: Write the failing tests**

```ts
describe('isDrag', () => {
    it('treats a move under 4 px as a click', () => {
        expect(isDrag({ x: 10, y: 10 }, { x: 12, y: 13 })).toBe(false); // 3.6 px
    });
    it('treats a move of 4 px or more as a drag', () => {
        expect(isDrag({ x: 10, y: 10 }, { x: 14, y: 10 })).toBe(true);
    });
});

describe('getMissingAxis', () => {
    it.each([['top', 2], ['perspective', 2], ['side', 0], ['front', 1]] as const)(
        '%s misses axis %i', (mode, axis) => expect(getMissingAxis(mode)).toBe(axis)
    );
});

describe('getDraftRectangle', () => {
    it('spans the two corners in the top view', () => {
        expect(getDraftRectangle('top', [1, 2, -0.5], [5, 4, -0.5])).toEqual({
            missingAxis: 2, planeCoordinate: -0.5, min: [1, 2, -0.5], max: [5, 4, -0.5]
        });
    });
    it('gives the same rectangle for a reversed drag', () => {
        expect(getDraftRectangle('top', [5, 4, -0.5], [1, 2, -0.5]))
            .toEqual(getDraftRectangle('top', [1, 2, -0.5], [5, 4, -0.5]));
    });
    it('uses Y and Z in the side view', () => {
        const r = getDraftRectangle('side', [7, 0, 0], [7, 4, 2]);
        expect(r).toMatchObject({ missingAxis: 0, planeCoordinate: 7, min: [7, 0, 0], max: [7, 4, 2] });
    });
    it('uses X and Z in the front view', () => {
        const r = getDraftRectangle('front', [0, 3, 0], [4, 3, 2]);
        expect(r).toMatchObject({ missingAxis: 1, planeCoordinate: 3 });
    });
});

describe('getDraftBox', () => {
    const rectangle = getDraftRectangle('top', [1, 2, 0], [5, 4, 0]);
    it('returns a flat preview box without an extent', () => {
        expect(getDraftBox(rectangle)).toEqual({ center: [3, 3, 0], size: [4, 2, 0.1] });
    });
    it('spans the extent on the missing axis', () => {
        expect(getDraftBox(rectangle, { min: 0, max: 1.5 }))
            .toEqual({ center: [3, 3, 0.75], size: [4, 2, 1.5] });
    });
    it('clamps a near-zero side to 0.1 without moving the centre', () => {
        const thin = getDraftRectangle('top', [1, 2, 0], [1.01, 4, 0]);
        const box = getDraftBox(thin, { min: 0, max: 1 });
        expect(box.size[0]).toBe(0.1);
        expect(box.center[0]).toBeCloseTo(1.005);
    });
});

describe('getDefaultCuboidBox', () => {
    it('returns a cube of 2% of the diagonal resting on the position', () => {
        const bounds = { min: [0, 0, 0], max: [30, 40, 0] } as const; // diagonal 50
        expect(getDefaultCuboidBox([2, 3, 0], bounds))
            .toEqual({ center: [2, 3, 0.5], size: [1, 1, 1] });
    });
    it('uses the 0.1 minimum for empty bounds', () => {
        const bounds = { min: [0, 0, 0], max: [0, 0, 0] } as const;
        expect(getDefaultCuboidBox([0, 0, 0], bounds).size).toEqual([0.1, 0.1, 0.1]);
    });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npm run test:unit -- --run src/lib/components/PointCloudLabelingWorkspace/CuboidDraft/cuboidDraft.test.ts`
Expected: FAIL, module not found.

- [ ] **Step 3: Implement the exports listed under Produces**

`getDefaultCuboidBox` carries over the formula of `computeDefaultCuboidSize` in `WS/useCreateCuboidAnnotation/useCreateCuboidAnnotation.svelte.ts` (the hook keeps its copy until Task 3).

- [ ] **Step 4: Run to verify it passes**

Same command. Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/lib/components/PointCloudLabelingWorkspace/CuboidDraft/cuboidDraft.ts src/lib/components/PointCloudLabelingWorkspace/CuboidDraft/cuboidDraft.test.ts
git commit -m "Add cuboid draft geometry (ENT-565)"
```

### Task 2: Fit to points (`fitCuboidToPoints.ts`)

**Files:**
- Create: `WS/CuboidDraft/fitCuboidToPoints.ts`
- Test: `WS/CuboidDraft/fitCuboidToPoints.test.ts`

**Interfaces:**
- Consumes: `DraftRectangle`, `AxisExtent` from Task 1; `PointBatch` from `$lib/components/PointCloudViewer`.
- Produces:

```ts
/** Extent of the missing axis from the points inside the rectangle, or the fallback. */
export function fitMissingAxis(rectangle: DraftRectangle, batch: PointBatch | undefined): AxisExtent;
```

Rules: read `batch.segments ?? [batch]`, and only the first `count` points of each. A point is inside when both in-plane coordinates lie within `rectangle.min..rectangle.max`, borders included. Result is the minimum and maximum of the inside points on `missingAxis`. Fallback when no point is inside or `batch` is undefined: let `s` be the shorter in-plane side of the rectangle; for `missingAxis === 2` return `{ min: planeCoordinate, max: planeCoordinate + s }`, otherwise `{ min: planeCoordinate - s / 2, max: planeCoordinate + s / 2 }`.

- [ ] **Step 1: Write the failing tests** (Z values are exact in float32 so `toEqual` holds)

```ts
const batch = (points: number[], count = points.length / 3): PointBatch => ({
    positions: new Float32Array(points), intensities: new Float32Array(count), count
});
const top = getDraftRectangle('top', [0, 0, -1], [4, 2, -1]);

it('fits Z to the points inside a top-view rectangle', () => {
    const points = [1, 1, 0.25, 3, 1, 1.75, 9, 9, 50]; // last point is outside
    expect(fitMissingAxis(top, batch(points))).toEqual({ min: 0.25, max: 1.75 });
});
it('counts points on the rectangle border as inside', () => {
    expect(fitMissingAxis(top, batch([0, 0, 0.5, 4, 2, 1.5]))).toEqual({ min: 0.5, max: 1.5 });
});
it('fits X in the side view', () => {
    const side = getDraftRectangle('side', [5, 0, 0], [5, 4, 2]);
    expect(fitMissingAxis(side, batch([1, 1, 1, 3, 2, 1]))).toEqual({ min: 1, max: 3 });
});
it('fits Y in the front view', () => {
    const front = getDraftRectangle('front', [0, 5, 0], [4, 5, 2]);
    expect(fitMissingAxis(front, batch([1, -2, 1, 2, 6, 1]))).toEqual({ min: -2, max: 6 });
});
it('ignores points beyond count', () => {
    expect(fitMissingAxis(top, batch([1, 1, 0.5, 1, 1, 99], 1))).toEqual({ min: 0.5, max: 0.5 });
});
it('reads every accumulated segment', () => {
    const merged = { ...batch([]), segments: [batch([1, 1, 0.25]), batch([2, 1, 1.5])] };
    expect(fitMissingAxis(top, merged)).toEqual({ min: 0.25, max: 1.5 });
});
it('rests on the plane with the shorter side as height when no point is inside', () => {
    expect(fitMissingAxis(top, batch([9, 9, 9]))).toEqual({ min: -1, max: 1 });
});
it('centres on the plane in side and front views when no point is inside', () => {
    const side = getDraftRectangle('side', [5, 0, 0], [5, 4, 2]);
    expect(fitMissingAxis(side, undefined)).toEqual({ min: 4, max: 6 });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npm run test:unit -- --run src/lib/components/PointCloudLabelingWorkspace/CuboidDraft/fitCuboidToPoints.test.ts`
Expected: FAIL, module not found.

- [ ] **Step 3: Implement `fitMissingAxis`** as one pass over the positions, no allocation per point.

- [ ] **Step 4: Run to verify it passes**

- [ ] **Step 5: Commit**

```bash
git add src/lib/components/PointCloudLabelingWorkspace/CuboidDraft/fitCuboidToPoints.ts src/lib/components/PointCloudLabelingWorkspace/CuboidDraft/fitCuboidToPoints.test.ts
git commit -m "Fit a drafted cuboid to the points inside it (ENT-565)"
```

### Task 3: Placement argument through the create chain

**Files:**
- Modify: `WS/useCreateCuboidAnnotation/useCreateCuboidAnnotation.svelte.ts`
- Modify: `WS/useCreateCuboidAnnotation/useCreateCuboidAnnotation.svelte.test.ts`
- Modify (type of the argument only, `Vector3` → `CuboidPlacement`): `WS/useWorkspaceEditing/useWorkspaceEditing.svelte.ts:144`, `WS/pointCloudWorkspaceLayoutContext.svelte.ts:94`, `WS/SceneViewport/SceneViewport.svelte:40`, `WS/SceneViewport/sceneViewportProps.d.ts:62`, `WS/CuboidLayer/CuboidLayer.svelte:25`, `WS/CuboidLayer/cuboidLayerProps.d.ts:26`
- Modify: `WS/CuboidLayer/CuboidLayer.svelte:103` — temporary adapter `onclick={(p) => onCreateCuboid?.({ kind: 'drop', position: p })}` until Task 5.

**Interfaces:**
- Consumes: `CuboidPlacement`, `getDefaultCuboidBox` from Task 1.
- Produces: `handleCreateCuboid(placement: CuboidPlacement, onCreated: (annotationId: string) => void | Promise<void>): Promise<void>`; `onCreateCuboid?: (placement: CuboidPlacement) => void` on every layer listed above.

- [ ] **Step 1: Update the hook tests**

Every existing call `handleCreateCuboid([x, y, z], …)` becomes `handleCreateCuboid({ kind: 'drop', position: [x, y, z] }, …)`; the assertions of the test at line 86 stay as they are (same geometry as today). Add:

```ts
it('saves a drawn box with its own centre and size', async () => {
    // same setup as 'creates a cuboid with the remembered class and scene frame geometry'
    await useCreateCuboidAnnotation(params).handleCreateCuboid(
        { kind: 'box', box: { center: [1, 2, 3], size: [4, 5, 6] } },
        vi.fn()
    );
    expect(createAnnotation).toHaveBeenCalledWith(
        expect.objectContaining({
            cuboid_3d: expect.objectContaining({
                px: 1, py: 2, pz: 3, sx: 4, sy: 5, sz: 6, qx: 0, qy: 0, qz: 0, qw: 1
            })
        })
    );
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npm run test:unit -- --run src/lib/components/PointCloudLabelingWorkspace/useCreateCuboidAnnotation`
Expected: FAIL (type error or wrong geometry for the box case).

- [ ] **Step 3: Change the hook**

`buildCuboidInput` takes a `CuboidBox`. `handleCreateCuboid` resolves the placement first: `'drop'` → `getDefaultCuboidBox(position, capturedFrame?.bounds ?? ZERO_BOUNDS)`, `'box'` → its box. Delete `computeDefaultCuboidSize` from the hook.

- [ ] **Step 4: Change the argument type in the files listed above and add the adapter in `CuboidLayer.svelte`**

- [ ] **Step 5: Run tests and type check**

Run: `npm run test:unit -- --run src/lib/components/PointCloudLabelingWorkspace` then `npm run check`
Expected: PASS, 0 errors.

- [ ] **Step 6: Commit**

```bash
git add -u src/lib/components/PointCloudLabelingWorkspace
git commit -m "Pass a cuboid placement through the create chain (ENT-565)"
```

### Task 4: Draft hook (`useCuboidDraft`)

**Files:**
- Create: `WS/CuboidDraft/useCuboidDraft/useCuboidDraft.svelte.ts`
- Create: `WS/CuboidDraft/useCuboidDraft/CuboidDraftHarness.svelte`
- Test: `WS/CuboidDraft/useCuboidDraft/useCuboidDraft.svelte.test.ts`

Follow the structure, the Threlte mocking and the `pointer()` event helper of `WS/CuboidLayer/CuboidFaceResize/useCuboidFaceResize/` (hook, harness, test).

**Interfaces:**
- Consumes: everything from Tasks 1 and 2; `useThrelte()` for `camera` and `renderer.domElement`.
- Produces:

```ts
interface PlanePointerEvent {
    /** World-space hit on the plane mesh. */
    point: { x: number; y: number; z: number };
    nativeEvent: PointerEvent;
}
interface Params {
    getCameraMode: () => CameraMode;
    getBatch: () => PointBatch | undefined;
    onCreate: (placement: CuboidPlacement) => void;
}
export function useCuboidDraft(params: Params): {
    /** Box to preview, or null when no drag is active. */
    readonly previewBox: CuboidBox | null;
    handlePlanePointerDown: (event: PlanePointerEvent) => void;
};
```

Behaviour:
- `handlePlanePointerDown` ignores any button other than 0. Otherwise it stores the start screen point and world point, captures the pointer on the canvas, and adds canvas listeners for `pointermove`, `pointerup`, `pointercancel`, `lostpointercapture`, `contextmenu`, and a window `keydown` listener.
- `pointermove`: convert `clientX/clientY` to a world point by raycasting from the camera onto a `THREE.Plane` whose normal is the missing axis and which passes through the start world point. If the ray misses (`null`), ignore the move. Once `isDrag` is true, `previewBox = getDraftBox(getDraftRectangle(mode, start, current))`.
- `pointerup`, not a drag: `onCreate({ kind: 'drop', position: start })`.
- `pointerup`, a drag, camera mode `top` / `side` / `front`: `onCreate({ kind: 'box', box: getDraftBox(rectangle, fitMissingAxis(rectangle, getBatch())) })`.
- `pointerup`, a drag, camera mode `perspective`: discard the draft, create nothing (Task 6 replaces this).
- `Escape`, `contextmenu` (also `preventDefault()`), `pointercancel`, `lostpointercapture`, a change of `getBatch()` identity, and unmount: discard the draft, remove the listeners, `previewBox = null`.

- [ ] **Step 1: Write the failing tests**

Harness setup: orthographic camera looking down −Z for the `top` mode so that 1 px = a known world distance; canvas `getBoundingClientRect` stubbed to 400 × 400. Tests (name → assertion):

```ts
it('drops a default cuboid on a click', …);
// down at (200,200) with point [0,0,0], up at (201,201)
// → onCreate called once with { kind: 'drop', position: [0, 0, 0] }

it('creates a fitted box after a drag in the top view', …);
// batch with points [1,1,0.25] and [2,1,1.75] inside the dragged rectangle
// → onCreate called once with kind 'box', box.size[2] === 1.5, box.center[2] === 1

it('shows a flat preview while dragging and clears it on release', …);
// after pointermove: previewBox.size[2] === 0.1; after pointerup: previewBox === null

it('creates nothing after a drag in the perspective view', …);

it.each(['Escape', 'contextmenu', 'pointercancel', 'lostpointercapture', 'unmount'])(
    'discards the draft on %s', …);
// onCreate not called, previewBox === null, a later pointerup does nothing

it('prevents the context menu during a draft', …);
// dispatched contextmenu event has defaultPrevented === true

it.each([1, 2])('ignores pointer-down with button %i', …);
// onCreate not called after pointerup, previewBox stays null

it('keeps the last preview when the ray misses the plane', …);
// perspective camera looking horizontally; pointermove above the horizon → previewBox unchanged

it('discards the draft when the batch changes', …);
```

- [ ] **Step 2: Run to verify it fails**

Run: `npm run test:unit -- --run src/lib/components/PointCloudLabelingWorkspace/CuboidDraft/useCuboidDraft`
Expected: FAIL, module not found.

- [ ] **Step 3: Implement the hook and the harness**

- [ ] **Step 4: Run to verify it passes**

- [ ] **Step 5: Commit**

```bash
git add src/lib/components/PointCloudLabelingWorkspace/CuboidDraft/useCuboidDraft
git commit -m "Add the cuboid draft pointer hook (ENT-565)"
```

### Task 5: Scene components, wiring, changelog

**Files:**
- Create: `WS/CuboidDraft/CuboidDraftPreview.svelte`, `WS/CuboidDraft/CuboidDraftPreview.stories.svelte`
- Create: `WS/CuboidDraft/CuboidDraftTarget.svelte`, `WS/CuboidDraft/index.ts`
- Modify: `WS/CuboidLayer/CuboidLayer.svelte`, `WS/CuboidLayer/cuboidLayerProps.d.ts`, `WS/CuboidLayer/CuboidLayer.test.ts`
- Modify: `WS/SceneViewport/SceneViewportCanvas/SceneViewportCanvas.svelte`
- Delete: `WS/GroundPlane/GroundPlaneClickTarget/GroundPlaneClickTarget.svelte`; remove its line from `WS/GroundPlane/index.ts`
- Modify: `../CHANGELOG.md`

**Interfaces:**
- Consumes: `useCuboidDraft` (Task 4), `getCuboidCreationPlane` (existing).
- Produces:
  - `CuboidDraftPreview` props: `{ box: CuboidBox }`. Renders a `T.Mesh` with `BoxGeometry` at `box.center` and `box.size`, `MeshBasicMaterial` white, `transparent`, `opacity` 0.2, `depthWrite` false, plus `T.LineSegments` over an `EdgesGeometry` of the same box in white.
  - `CuboidDraftTarget` props: `{ bounds: Bounds3; cameraMode?: CameraMode; batch?: PointBatch; onCreateCuboid: (placement: CuboidPlacement) => void }`. Renders the same invisible plane mesh as `GroundPlaneClickTarget` with `onpointerdown={draft.handlePlanePointerDown}` instead of `onclick`, and `<CuboidDraftPreview>` when `draft.previewBox` is set.
  - `CuboidLayer` new optional prop `pointBatch?: PointBatch` ("Points of the current tick, used to fit a drawn cuboid.").

- [ ] **Step 1: Write the failing layer test** in `CuboidLayer.test.ts`

```ts
it('mounts the draft target only for the create-cuboid tool', …);
// mock '../CuboidDraft' with a stub component that records its props
// activeTool 'select' → stub not rendered
// activeTool 'create-cuboid' → stub rendered with bounds, cameraMode, batch === pointBatch
// calling the stub's onCreateCuboid with a placement → onCreateCuboid prop called with it
```

- [ ] **Step 2: Run to verify it fails**

Run: `npm run test:unit -- --run src/lib/components/PointCloudLabelingWorkspace/CuboidLayer/CuboidLayer.test.ts`
Expected: FAIL.

- [ ] **Step 3: Create the two components, the story and `index.ts`**

The story shows one preview box over the fixture point cloud used by `WS/CuboidLayer/CuboidLayer.stories.svelte`.

- [ ] **Step 4: Wire it up**

`CuboidLayer.svelte`: replace `GroundPlaneClickTarget` (and the Task 3 adapter) with `<CuboidDraftTarget bounds={groundPlaneBounds} {cameraMode} batch={pointBatch} onCreateCuboid={(p) => onCreateCuboid?.(p)} />`. `SceneViewportCanvas.svelte`: pass `pointBatch={props.batch}` to `CuboidLayer`. Delete `GroundPlaneClickTarget.svelte` and its export.

- [ ] **Step 5: Add the changelog entry** under `## [Unreleased]` → `### Added`

```markdown
- Draw a cuboid by dragging a rectangle in the top, side or front view of the point cloud workspace. The remaining dimension is fitted to the points inside the rectangle.
```

- [ ] **Step 6: Run all checks**

Run: `npm run test:unit -- --run src/lib/components/PointCloudLabelingWorkspace` and `make static-checks`
Expected: PASS, no errors.

- [ ] **Step 7: Check by hand in the app**

Top, side and front views: a drag creates a fitted cuboid; a click drops the default cube; Escape and right-click cancel. 3D view: a click drops the default cube; a drag creates nothing and does not move the camera.

- [ ] **Step 8: Commit**

```bash
git add -A src/lib/components/PointCloudLabelingWorkspace ../CHANGELOG.md
git commit -m "Draw cuboids by dragging in orthographic views (ENT-565)"
```

---

## PR 2 — Drawing in the 3D view

### Task 6: Height step

**Files:**
- Modify: `WS/CuboidDraft/cuboidDraft.ts`, `WS/CuboidDraft/cuboidDraft.test.ts`
- Modify: `WS/CuboidDraft/useCuboidDraft/useCuboidDraft.svelte.ts`, `…/useCuboidDraft.svelte.test.ts`

**Interfaces:**
- Produces in `cuboidDraft.ts`:

```ts
/** Extent of a footprint raised from its plane to the given world Z. */
export function getHeightExtent(rectangle: DraftRectangle, z: number): AxisExtent;
// → { min: planeCoordinate, max: max(z, planeCoordinate + MIN_CUBOID_EXTENT) }
```

- Hook behaviour change, `perspective` only: a `pointerup` after a drag keeps the listeners and enters the height step with the footprint rectangle. In the height step:
  - `pointermove`: raycast onto a vertical `THREE.Plane` through the footprint centre whose normal is the camera's view direction with its Z component set to 0 (normalised; if its length is 0, ignore the move). `previewBox = getDraftBox(rectangle, getHeightExtent(rectangle, hit.z))`.
  - Canvas `pointerdown` with button 0: `onCreate({ kind: 'box', box: previewBox })`, then reset. With button 2: discard.
  - All discard triggers of Task 4 still apply.
  - `handlePlanePointerDown` does nothing while the height step is active.

- [ ] **Step 1: Write the failing tests**

```ts
// cuboidDraft.test.ts
it('raises the footprint from its plane to the pointer height', () => {
    const r = getDraftRectangle('perspective', [0, 0, -1], [4, 2, -1]);
    expect(getHeightExtent(r, 1.5)).toEqual({ min: -1, max: 1.5 });
});
it('keeps the 0.1 minimum when the pointer is below the plane', () => {
    const r = getDraftRectangle('perspective', [0, 0, -1], [4, 2, -1]);
    expect(getHeightExtent(r, -3)).toEqual({ min: -1, max: -0.9 });
});

// useCuboidDraft.svelte.test.ts — replace 'creates nothing after a drag in the perspective view'
it('keeps the footprint preview after the drag in the perspective view', …);
// after pointerup: onCreate not called, previewBox !== null
it('sets the height from pointer movement and saves on click', …);
// pointermove up, then pointerdown button 0 → onCreate called once with kind 'box',
// box.size[2] > 0.1, box.center[2] === plane + size[2] / 2
it.each(['Escape', 'contextmenu', 'right pointer-down'])('discards the height step on %s', …);
it('does not start a second draft during the height step', …);
```

- [ ] **Step 2: Run to verify it fails**

Run: `npm run test:unit -- --run src/lib/components/PointCloudLabelingWorkspace/CuboidDraft`
Expected: FAIL.

- [ ] **Step 3: Implement `getHeightExtent` and the height step in the hook**

- [ ] **Step 4: Run to verify it passes**

- [ ] **Step 5: Commit**

```bash
git add -u src/lib/components/PointCloudLabelingWorkspace/CuboidDraft
git commit -m "Set cuboid height with a second step in the 3D view (ENT-565)"
```

### Task 7: Changelog and manual check

**Files:**
- Modify: `../CHANGELOG.md`

- [ ] **Step 1: Replace the PR 1 entry** with

```markdown
- Draw a cuboid by dragging in the point cloud workspace. In the top, side and front views one drag draws a rectangle and the remaining dimension is fitted to the points inside it. In the 3D view, drag the footprint, move the mouse to set the height and click to confirm.
```

(If PR 1 is already released, add a new entry for the 3D view instead.)

- [ ] **Step 2: Run all checks**

Run: `npm run test:unit -- --run src/lib/components/PointCloudLabelingWorkspace` and `make static-checks`
Expected: PASS.

- [ ] **Step 3: Check by hand in the app**

3D view: drag, release, move, click creates a cuboid of the drawn footprint and height; Escape and right-click cancel in both steps; the camera does not move during either step; "add track" still starts a track from the drawn cuboid.

- [ ] **Step 4: Commit**

```bash
git add ../CHANGELOG.md
git commit -m "Describe 3D cuboid drawing in the changelog (ENT-565)"
```
