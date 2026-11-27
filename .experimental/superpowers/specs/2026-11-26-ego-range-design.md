# Ego range: distance from the ego vehicle and range highlighting

## Intent

Labelling guidelines require annotators to label every object within 40 m of the ego vehicle.
The point-cloud workspace shows no distances, so annotators guess. Most objects that still need
a label have no cuboid yet, so the core of the feature is a visual on the point cloud.
Per-cuboid distances help with borderline cases.

## Goals

- A ring at the range radius, centered on the ego, in the ground plane.
- Lidar points beyond the radius are dimmed.
- Each cuboid shows its flat distance from the ego, e.g. `38.2 m`, and a marker when it is
  beyond the range.
- Works in any reference frame, including world frames (`map`, `odom`).
- Off by default. Radius configurable, default 40 m, clamped to 1–500 m.

Non-goals: filtering by distance, range visuals in the camera strip, 3D distance.

Never fall back to the frame origin when the ego position is unknown: in a world frame that
would mark the wrong objects. Show nothing and a notice instead.

## Design

### Backend

`GET /datasets/{dataset_id}/mcap-sequences/{sequence_id}/ticks/{seq_number}/ego-position`
with required query parameters `target_frame_id` and `ego_frame_id` (`EgoPositionFrames`).

`TickEgoPositionView.position` is the origin of the ego frame in the target frame at the tick
timestamp, as `[x, y, z]`:

- `[0, 0, 0]` if the frames are the same.
- `None` if the tick has no timestamp or no transform chain connects the frames.
- 404 if the tick does not exist.

The service uses the same transform machinery as the camera projections in
`get_tick_details`. It is a separate endpoint so the tick details cache keys stay unchanged
during playback, and the request is only made while the feature is on.

### Frontend

Code lives in `PointCloudLabelingWorkspace/EgoRange/`. `useEgoRange` owns the settings, the
ego position query, and the notice. The workspace controller exposes it to the scene settings,
the viewport, and the annotation list.

- **Settings** (scene settings popover): "Show ego range", "Radius (m)", "Ego frame". The ego
  frame options are the sequence's `reference_frames`; the default is the stored frame for the
  dataset, else `CABIN`, else `base_link`, else none. Stored in local storage; the ego frame
  per dataset ID.
- **Ring and distance line**: amber, not pickable, drawn in the 3D and Top views only. The
  distance line runs to the selected cuboid.
- **Dimming**: points beyond the radius drop to 25% brightness. The range is dimmed before the
  cuboid highlight, so a selected cuboid beyond the range stays bright.
- **Playback**: the previous position stays in use while the next tick loads, but only for
  the same reference and ego frames.
- **Notices**: no ego frame, point clouds in sensor frames (position not requested), or
  position `None` / request failed.
- **Cuboid distances**: `hypot(dx, dy)` to the cuboid center, in the expanded annotation row
  (`AnnotationEgoDistance`), with a "beyond range" marker.
