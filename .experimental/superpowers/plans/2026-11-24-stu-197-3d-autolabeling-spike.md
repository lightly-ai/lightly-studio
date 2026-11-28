# STU-197: 3D autolabeling spike plan

Date: 2026-11-24
Issue: https://linear.app/lightly/issue/STU-197/figure-out-autolabeling-for-3d-point-cloud-labeling
Status: spike (throwaway code, no tests, not for merge)

## Goal

Find out which autolabeling approach gives usable 3D cuboids on our MCAP point cloud
data, cheaply enough to ship. The output is numbers and a recommendation, not product code.

## Decisions so far

- Parked: lifting 2D SAM masks to 3D. Too many moving parts (five cameras, calibration,
  sync, paid vendor call) for mediocre boxes.
- Parked: pretrained automotive detectors (CenterPoint / PointPillars weights from
  nuScenes, KITTI, Waymo). Wrong sensor and classes for our data, and the weights
  licence needs checking.
- Trying: geometry-first tools (no ML), then a model trained on our own labels.
- Main interaction is a brush that preselects points, then a cuboid is fitted to them
  (agreed with a colleague on 2026-11-24). Click-to-cuboid stays only as a baseline.

## Experiments

Each experiment is an offline Python script that reads MCAP recordings directly and
scores its output against the existing ground truth topic
(`/platform/perception/visualization/detections_3d_ground_truth`).

### E0. Data inventory

What do we have: recordings, ticks, lidars, points per frame, labeled frames, cuboids
per class, share of static vs moving objects.
Decides: whether E4 is possible at all, and which classes E1 to E3 are scored on.

### E1. Brush-to-cuboid

The user paints the points of an object with a brush, and we fit a cuboid to the
painted points. The brush replaces the single click as the main interaction: the user
decides what belongs to the object, so we do not have to guess it by clustering.

Simulate the brush offline: take the points inside a ground truth cuboid, then keep
only part of them (strokes as seen from one viewpoint) and add some spill (ground and
neighbouring points that a real brush would catch).

Variants to compare:

- A. Fit an oriented box to the painted points only.
- B. A plus cleanup: drop ground and outlier points before fitting.
- C. B plus growing: extend the selection to connected points the brush missed.
- D. Baseline: single click plus clustering, no brush.

Measure: 3D IoU and BEV IoU against ground truth, centre error, yaw error, time per
fit, each at 10% / 25% / 50% / 100% of the object's points painted and at several
spill levels. The key curve is IoU against how much the user has to paint.
Proposed bar: median 3D IoU >= 0.5 with 25% of the points painted, under 200 ms on CPU.

Also test on `truck_bed` and `truck_cabin`: painting only the part should give the
part's box, which the click baseline cannot do.

### E2. Static object propagation through the `map` frame

Take one ground truth cuboid, express it in `map`, re-project it onto every other tick.
Measure: IoU against ground truth per tick, and the share of objects for which this
works (static objects).
Decides: whether "label once, get the whole sequence" is real for our data.

### E3. Snap a rough box to the points

Start from a perturbed or interpolated cuboid and refine it against the points.
Measure: IoU before and after.
Decides: whether track interpolation can be upgraded with point-based refinement.

### E4. Own model (only if E0 shows enough labels)

Train PointPillars from scratch with OpenPCDet (Apache 2.0, no sparse conv) on our
ground truth, with held-out sequences. Runs on a GPU outside Studio.
Rough threshold to bother: about 500 labeled frames or more.
Measure: mAP per class, inference time, and how the score grows with 10% / 25% / 50% /
100% of the labels (this tells us how much a customer must label before it pays off).

### E5. Workflow draft

Only after E1 to E4. How the winning pieces show up in the 3D workspace: trigger,
confidence, accept / edit / reject. Predictions enter with `confidence`, which the
annotation model already has.

## Order

E0 -> E1 -> E2 -> E3, then E4 if the data allows, then E5.

## Where things live

- Spike code and results: `.experimental/stu-197-3d-autolabeling/`
- Nothing is committed yet. The repo is currently on another person's branch; commit
  from `kondrat-stu-197-figure-out-autolabeling-for-3d-point-cloud` when ready.

## Open questions

- Which customers and data is this for (sensors, scenes, classes)?
- Brush details: does it paint in the 3D view (screen-space disc that selects all points
  behind it, or only the nearest surface) or in the orthographic views? Can strokes add
  and erase? This sets how much spill E1 has to survive.
- Is the brush only for cuboids, or also the start of point-level segmentation labels?
- Is the ground truth topic human-labeled or model output? If model output, E1 to E4
  scores are only relative.
- Where would customer-specific training run in the product (GPU, job handling)?
- Licence check before any pretrained weights are reconsidered.

## Log

- 2026-11-24: plan written. Data is not in the repo (`lightly_studio/datasets` links to
  `~/Projects/dataset_examples/`), access needed to start E0.
- 2026-11-24: E0, partial, from the local Studio database only (`lightly_studio/lightly_studio.db`,
  read from a copy). Point clouds not inspected yet.
  - 1 recording (`mcap_with_issue/rosbag2_2026_09_15-23_06_38_0.mcap`), 1 sequence, 654 ticks.
  - 2616 cuboids = 4 object tracks x 654 ticks, all in frame `odom`, no confidence values.
  - Classes: `truck` (about 11.7 x 5.4 x 4.1 m), `truck_bed`, `truck_cabin`, `person`.
    Bed and cabin are parts of the truck.
  - The truck moves about 20 m over the sequence, the person a few metres.
    202 cuboids are marked interpolated (200 of them on the person).
  - Consequences:
    - E4 cannot be evaluated on this data: one scene, one truck, one person. A model
      would memorise it. Needs many more labeled sequences.
    - E2 has no labeled static object here. It can only be tested on stretches where
      the truck stands still.
    - E1 can target `truck` and `person`. Geometry alone cannot split a truck into bed
      and cabin, so part-level boxes need another idea (class size priors or a model).
- 2026-11-24: plan adjusted. E1 is now brush-to-cuboid instead of click-to-cuboid. Painting
  only a part should also solve the bed / cabin split noted above. No brush or lasso
  exists in the point cloud workspace yet, so E5 has to include the brush tool itself.
