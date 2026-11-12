# Adjustable 3D cuboid creation — design

Issue: [ENT-565](https://linear.app/lightly/issue/ENT-565/make-initial-3d-cuboid-creation-adjustable)
Date: 2026-11-12

## Problem

With the **Create cuboid** tool, one click drops a fixed-size, world-aligned cube
(edge = 2% of the scene diagonal, minimum 0.1). The size is rarely right, so users
create the cuboid and then resize it. Press-and-drag does nothing. Feedback from
testing: the expected flow is to draw a rectangle spanning the object in one
orthographic view, then adjust in another view, so that a cuboid takes 2–3 actions.

## Goal

Users set the cuboid's size while creating it, by dragging, in every view. The
interaction follows the box-creation pattern of Blender and 3ds Max.

## Behaviour

| Situation | Behaviour |
|---|---|
| Drag in top, side or front view | One drag draws a rectangle. The third dimension is fitted to the points inside it. Release saves. |
| Drag in the 3D (perspective) view | Drag draws the footprint on the ground. Release, move the mouse to set the height, click to save. |
| Click without dragging | Quick-drop of the default-size cube, as today. |
| Orientation | Always world-aligned (identity quaternion). Users rotate afterwards with the Rotate tool. |
| Cancel | Escape or right-click at any step before saving. Changing the tool or the tick also discards the draft. |

After a draw completes, the flow is unchanged: class dialog if no class is
remembered, save, select the new cuboid, switch to the Select tool, attach to a
track when "add track" is on.

### Click versus drag

A pointer-down followed by a pointer-up less than 4 screen pixels away is a click.
Anything else is a drag.

### Orthographic views

| View | Rectangle sets | Fitted to points |
|---|---|---|
| Top | X, Y | Z (height) |
| Side | Y, Z | X (depth) |
| Front | X, Z | Y (depth) |

- The fit takes every point whose two in-plane coordinates fall inside the
  rectangle and sets the box limits on the remaining axis to the minimum and
  maximum of those points.
- If no point falls inside, the third dimension equals the shorter side of the
  rectangle. In the top view the box rests on the ground plane. In the side and
  front views it is centred on the scene's depth midpoint (the current creation
  plane).

### 3D view

1. Pointer-down and drag: the footprint rectangle is drawn on the ground plane.
   The preview is flat.
2. Pointer-up: the draft enters the height step. Height is the Z of the
   intersection between the pointer ray and a vertical plane through the
   footprint centre that faces the camera, minus the ground Z.
3. Click: confirm and save.

### Size limits

Every dimension is clamped to a minimum of 0.1, the current minimum, so a cuboid
never has a zero extent.

### Known limitation

The fit uses the extreme points without outlier filtering. An overhanging branch
in the top view, or other objects along the line of sight in the side and front
views, produce a box that is too large. Users correct it with the resize handles.

## Architecture

The creation logic lives in plain TypeScript, separate from the scene. A thin
scene component feeds pointer events into it and renders a preview.

New files in `lightly_studio_view/src/lib/components/PointCloudLabelingWorkspace/CuboidDraft/`:

| File | Purpose | Depends on |
|---|---|---|
| `cuboidDraft.ts` | Holds the draft step (idle → dragging footprint → setting height (3D only) → done) and turns pointer positions into a box (centre and size). Also builds the default quick-drop box. | Nothing; pure functions |
| `fitCuboidToPoints.ts` | Given a rectangle, the missing axis and point positions, returns the extent and centre on that axis, or the fallback. | A `Float32Array` of positions |
| `useCuboidDraft/useCuboidDraft.svelte.ts` | Owns the pointer and keyboard listeners (pointer-down, move, up, Escape, right-click) and the draft step; emits the finished placement. Tested through a harness, like `useCuboidFaceResize`. | `cuboidDraft`, `fitCuboidToPoints` |
| `CuboidDraftTarget.svelte` | Replaces `GroundPlaneClickTarget`. Renders the invisible plane and the preview, and connects them to `useCuboidDraft`. | `useCuboidDraft`, existing `getCuboidCreationPlane` |
| `CuboidDraftPreview.svelte` | Renders a translucent box while a draft is active. | The current draft box |

Changes to existing code:

- `useCreateCuboidAnnotation` takes a placement instead of a ground position:
  either a drop point (click) or a finished box (drag). `computeDefaultCuboidSize`
  moves into `cuboidDraft.ts`; the hook calls it with the current frame's bounds,
  so a click produces the same box that is created today.
- `onCreateCuboid` in `CuboidLayer`, its props and `useWorkspaceEditing` changes
  its argument from a position to a placement.
- `CuboidLayer` receives the current frame's point positions and passes them to
  the fit.
- `GroundPlaneClickTarget.svelte` is removed. `cuboidCreationPlane.ts` stays.
- The camera needs no change: in the `create-cuboid` tool the left mouse button
  already neither rotates nor pans (`SceneCamera.svelte`).

Data flow:

1. Pointer events → `CuboidDraftTarget` → `cuboidDraft`.
2. `cuboidDraft` exposes the current box → `CuboidDraftPreview`.
3. On completion in an orthographic view, `fitCuboidToPoints` supplies the third
   dimension.
4. The placement goes to `onCreateCuboid`; the rest of the flow is unchanged.

The backend and the API do not change.

## Error handling

Save errors are handled as today, with the same toasts. There are no new server
errors. A cancelled draft saves nothing.

## Testing

| Unit | Checks |
|---|---|
| `cuboidDraft.ts` | Click versus drag threshold; box from two corners for each view; 3D height step; 0.1 minimum; cancel from every step |
| `fitCuboidToPoints.ts` | Fit on each axis; points outside the rectangle are ignored; fallback when no point is inside |
| `CuboidDraftTarget.svelte` | A drag calls `onCreateCuboid` with a box; Escape and right-click create nothing |
| `useCreateCuboidAnnotation` | Existing tests move to the box argument |
| `CuboidLayer`, workspace scene | Existing click tests still pass: a click creates the default cube |

A Storybook story covers `CuboidDraftPreview`. The change is also checked by hand
in the app in all four views.

## Delivery

Two pull requests, each useful on its own:

1. **Drawing in orthographic views.** Draft module without the height step,
   point fit, preview, replacement of `GroundPlaneClickTarget`, new argument for
   `useCreateCuboidAnnotation`, click as quick-drop. In the 3D view only the click
   works after this PR, as today; a drag there creates nothing. `CHANGELOG.md` entry.
2. **Drawing in the 3D view.** Height step in the draft, footprint drag on the
   ground, click to confirm. `CHANGELOG.md` entry.

## Out of scope

- Setting the heading while drawing.
- Outlier filtering in the point fit.
- A click that repeats the size of the last cuboid.
- A modifier key for setting the third dimension by hand in orthographic views.
- Backend and API changes.
