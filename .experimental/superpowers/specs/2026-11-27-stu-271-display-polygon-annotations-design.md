# STU-271: Display polygon annotations

## Why

Users can import polygon annotations (COCO, YOLO, Python API), but the GUI draws only each
polygon's bounding box. So users cannot check their polygon labels.

## Goal

Draw the real polygon wherever the GUI shows annotations, on images and video frames:

- Stroke in the label or source color, including custom colors and highlight states.
- Semi-transparent fill.
- All parts of a multi-part polygon.

Out of scope: drawing or editing polygons, and backend changes. The API already sends the vertices.

## Decisions

- **No bounding box around polygons.** The outline replaces it everywhere. The "show bounding boxes
  for segmentation" setting does not apply to polygons. The label tag stays at the top-left
  corner of the polygon's bounding box.
- **Fill rule `nonzero`, with every part wound the same way:** overlapping parts of one polygon
  do not cut holes in each other. `nonzero` alone is not enough: parts with opposite winding
  cancel where they overlap, and imported files do not fix the winding.

## Approaches

The GUI has two renderers: SVG for the detail view and video player, and canvas for the grids.
The open question was how to draw polygons in the grids.

1. **Add polygons to the canvas renderer (picked).** One renderer per surface, follows the
   existing box and mask pattern, and keeps large grids fast.
2. Overlay an SVG on grid tiles. Simpler drawing, but adds a second layer per tile and duplicates
   the scaling math.
3. Rasterize polygons to masks. Gives no outline and costs CPU for nothing.

## Design

- **Canvas (image and video frame grids, annotation crops grid):** a new polygon input next to
  boxes and masks. It is drawn after masks, filled and then stroked, in the worker and on the main
  thread. The crops grid hides its box for polygons, as it does for masks, and keeps the label.
- **SVG (detail view, video player):** one `<path>` per polygon, one subpath per part. It is also
  the click target.
- Tests that check the polygon's box now check the outline.

Left to the builder: stroke width and fill alpha (match boxes), and test layout.
