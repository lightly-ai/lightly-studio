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

Revised on 2026-11-12 after the first review of the feature: the cuboid gets its
heading while it is drawn, and the quick-drop click is removed.

| Situation | Behaviour |
|---|---|
| Top view | 1. Press on the first point and drag along one side of the object; release fixes the side. It sets the heading and the length. 2. Move the mouse and click to fix the width. The height is fitted to the points inside the footprint. |
| 3D (perspective) view | Steps 1 and 2 as in the top view, on the ground. 3. Move the mouse and click to fix the height. |
| Side or front view | One drag draws a rectangle. The third dimension is fitted to the points inside it. Release saves. The box is world-aligned. |
| Click without dragging | Top and 3D views: the click sets the first point, and the next click sets the end of the side. Side and front views: nothing. There is no quick-drop cube. |
| Orientation | Top and 3D views: the heading points from the first point to the end of the drawn side (rotation around the vertical axis). Side and front views: world-aligned. |
| Cancel | Escape or right-click at any step before saving. Changing the tool or the tick also discards the draft. |

After a draw completes, the flow is unchanged: class dialog if no class is
remembered, save, select the new cuboid, switch to the Select tool, attach to a
track when "add track" is on.

### Click versus drag

A pointer-down followed by a pointer-up less than 4 screen pixels away is a click.
Anything else is a drag.

### Fit to points

| View | Drawn | Fitted to points |
|---|---|---|
| Top | Angled footprint in X and Y | Z (height) |
| Side | Rectangle in Y, Z | X (depth) |
| Front | Rectangle in X, Z | Y (depth) |

- The fit takes every point inside the drawn footprint or rectangle and sets the
  box limits on the remaining axis to the minimum and maximum of those points.
- If no point falls inside, the third dimension equals the shorter side. In the
  top view the box rests on the ground plane. In the side and front views it is
  centred on the scene's depth midpoint (the current creation plane).

### Height step in the 3D view

Height is the Z of the intersection between the pointer ray and a vertical plane
through the footprint centre that faces the camera, minus the ground Z. When the
camera looks straight down, the height is fitted to the points, as in the top view.

### Highlight of the points in the draft

While a cuboid is drawn, the points that it takes in are highlighted in every
viewport. The other points keep their color. The first side has no area, so it
highlights nothing. The width step and the side and front rectangle highlight
the whole column of points along the axis that is not drawn yet. The height
step highlights the points up to the current height.

### Keyboard rotation of the 3D camera

Q and E orbit the camera around the vertical axis through the view target. The
camera height does not change.

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
| `cuboidDraft.ts` | Turns pointer positions into a box (centre, size and heading) for an axis-aligned rectangle or an angled footprint. | Nothing; pure functions |
| `fitCuboidToPoints.ts` | Given a rectangle, the missing axis and point positions, returns the extent and centre on that axis, or the fallback. | A `Float32Array` of positions |
| `useCuboidDraft/useCuboidDraft.svelte.ts` | Owns the pointer and keyboard listeners (pointer-down, move, up, Escape, right-click) and the draft step; emits the finished placement. Tested through a harness, like `useCuboidFaceResize`. | `cuboidDraft`, `fitCuboidToPoints` |
| `CuboidDraftTarget.svelte` | Replaces `GroundPlaneClickTarget`. Renders the invisible plane and the preview, and connects them to `useCuboidDraft`. | `useCuboidDraft`, existing `getCuboidCreationPlane` |
| `CuboidDraftPreview.svelte` | Renders a translucent box while a draft is active. | The current draft box |

Changes to existing code:

- `useCreateCuboidAnnotation` takes the drawn box (centre, size and heading)
  instead of a ground position. The default-size cube is removed.
- `onCreateCuboid` in `CuboidLayer`, its props and `useWorkspaceEditing` changes
  its argument from a position to a box.
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
| `cuboidDraft.ts` | Click versus drag threshold; box from two corners for the side and front views; angled footprint and its width; height extent; 0.1 minimum |
| `fitCuboidToPoints.ts` | Fit on each axis and inside an angled footprint; points outside are ignored; fallback when no point is inside |
| `useCuboidDraft` | Side, width and height steps; fitted height in the top view; a click without a drag creates nothing; cancel from every step |
| `CuboidDraftTarget.svelte` | A dragged side and a width click call `onCreateCuboid` with a box; Escape and right-click create nothing |
| `useCreateCuboidAnnotation` | Saves the centre, size and heading of the drawn box |

Storybook stories cover `CuboidDraftPreview` and, with a sample point cloud, drawing
in each view (`CuboidDraftTarget`). The change is also checked by hand
in the app in all four views.

## Delivery

Two pull requests, each useful on its own:

1. **Drawing in orthographic views.** Draft module without the height step,
   point fit, preview, replacement of `GroundPlaneClickTarget`, new argument for
   `useCreateCuboidAnnotation`. `CHANGELOG.md` entry.
2. **Drawing in the 3D view.** Height step in the draft, footprint drag on the
   ground, click to confirm. `CHANGELOG.md` entry.

## Out of scope

- Outlier filtering in the point fit.
- A click that repeats the size of the last cuboid.
- A modifier key for setting the third dimension by hand in orthographic views.
- Backend and API changes.
