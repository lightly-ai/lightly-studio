# STU-30: Polygon Annotations (Backend)

## Why

Users need outlines for irregular objects. Boxes are too coarse, and pixel masks are tedious when an outline is enough. Also, today a COCO polygon added as `SEGMENTATION_MASK` becomes a mask annotation with only a box: the vertices are dropped.

## Scope

- A polygon annotation: one or more parts (closed loops), no holes, on images and video frames.
- Add polygons from COCO and YOLO, and export them to COCO and YOLO.
- Polygons can be queried by their bounding box, and cropped for embeddings on images. Crops on video frames aren't supported, the same as for masks today.
- The dropped-vertices bug is fixed.
- Backend only. It ships before the frontend, and until then the GUI can't show polygons. That gap is accepted.
- One labelformat fix. 0.1.17 already reads and writes `MultiPolygon` for COCO and YOLO. But its YOLO segmentation reader crashes on images without a label file and on blank lines, both common in real datasets; its detection reader handles them. Fixing labelformat was chosen over a workaround in Studio, so other users get the fix too.

**Out of scope:** conversion between polygons and masks, holes, migrating existing masks (including the box-only ones), AI-assisted polygons, and polygon evaluation.

**Changes to the issue's requirements:**
- No polygon-to-mask conversion on export.
- Two new export entries become one extended COCO export and one new YOLO export (see Export).

## Data model

**A new type.** `AnnotationType.POLYGON` (`"polygon"`) gets its own details table, linked one-to-one like the other types. Users see "polygon" and "part", never "multipolygon". The glossary gets both terms.
*Not taken:* a polygon field on the segmentation annotation. One type would have two shapes, every mask reader would have to branch, and a row could hold both or neither.

**Storage.**
- `polygons` is a plain `JSON` column: `[[[x, y], ...], ...]` (parts, then vertices). It has the same shape as the API and labelformat's `MultiPolygon.polygons`, so no conversion code is needed.
- Vertices are float pixels in the original image, with the origin at the top-left corner, rounded to 0.001 px. Floats, unlike the integer boxes, keep coordinates lossless through COCO and YOLO round trips; that is also labelformat's model. Rounding about halves the size and transfer of UI-drawn vertices, and the precision lost can't be seen.
- Integer `x`, `y`, `width` and `height` are computed from the vertices on every write, rounded outward. Crops, sorting, filters and the query language read them, as they do for masks. *Not taken:* computing the box when it's read. That needs nested JSON unnesting written separately for DuckDB and PostgreSQL, and it can't be indexed.
- *Not taken:* flat `float8[]` plus part offsets. On PostgreSQL (1M polygons) it was only about 20% smaller and 15% faster to load. That doesn't pay for two columns that must stay in sync. `JSONB` was nearly twice as large. Nested arrays don't work because PostgreSQL arrays must be rectangular.
- Transfer to the frontend is bounded by page size: about 1.3 MB per grid page even with 200 polygons per image.

**Validation.** Every write goes through one function, because the database doesn't check the shape. It requires at least 1 part, at least 3 vertices per part and finite numbers, then rounds and computes the box.

**Editing.** Every edit sends the full polygon: move, add or remove a vertex, or add or remove a part. The update replaces the polygon and recomputes the box, so no per-vertex endpoints are needed. A direct box edit on a polygon is rejected *(my call)*.

**Python API.** `PolygonAnnotation` and `CreatePolygon`, mirroring the mask classes *(my call)*.

## Ingestion

A new public enum chooses what to read:

```python
class AnnotationTask(str, Enum):
    OBJECT_DETECTION = "object_detection"
    INSTANCE_SEGMENTATION = "instance_segmentation"
```

- **COCO** (`add_samples_from_coco`, `add_annotations_from_coco`): `annotation_task` defaults to `OBJECT_DETECTION`. With `INSTANCE_SEGMENTATION`, `iscrowd=0` entries become polygons and `iscrowd=1` entries become masks, so a mixed file like COCO 2017 comes in completely in one call.
- **YOLO** (`add_samples_from_yolo`, `add_annotations_from_yolo`): with `INSTANCE_SEGMENTATION`, each segmentation line becomes a single-part polygon.
- **Deprecation:** the old `annotation_type` on the COCO methods still works and raises a `DeprecationWarning`. `SEGMENTATION_MASK` maps to `INSTANCE_SEGMENTATION`. Passing both parameters raises `ValueError`. It is removed in a later minor release. Both the deprecation and the removal get changelog entries.
- *Not taken:*
  - Keeping only `SEGMENTATION_MASK`: it would also create polygons, which a caller doesn't expect.
  - Accepting both `SEGMENTATION_MASK` and `POLYGON` with the same behavior: two names for one thing.
  - Making each value strict (polygons only, or masks only): a mixed file would lose entries.
  The parameter chooses what to read from the file, which is a task, not the type that gets stored.
- **Invalid polygons:** parts with fewer than 3 vertices are dropped. An annotation with no valid parts is skipped, with one warning that gives the count. COCO 2017 has a few *(my call)*.
- **YouTube-VIS** keeps today's behavior until its follow-up. The shared ingestion helper is split so only image ingestion changes *(my call)*.

## Export

- **"Segmentation masks (COCO)" becomes "Instance segmentation (COCO)".** It writes polygons as `iscrowd=0` and masks as RLE with `iscrowd=1` in one file, as the COCO spec pairs them. *Not taken:* a separate polygons-only COCO export. A mixed dataset like COCO 2017 would lose its crowd masks on the way out. The docs note that COCOeval treats `iscrowd=1` as ignore regions; that is already true today.
- **New "Instance segmentation (YOLO)":** polygons only. YOLO has no mask encoding, so masks are skipped with a warning that gives the count. YOLO allows one polygon per object, so labelformat joins the parts with zero-width bridges, and a multi-part polygon comes back as one part.
- **Pascal VOC stays masks-only.** It shares the COCO export's annotation input, and labelformat's Pascal VOC writer already rasterizes polygons, so including polygons would quietly convert them to masks. That conversion is out of scope; the follow-up can reuse this labelformat code.
- **Python:** `to_coco_instance_segmentation` and `to_yolo_instance_segmentation`. `to_coco_segmentation_masks` is deprecated like `annotation_type` *(my call)*.

## Other changes

- The query language and the Python query API get polygon `x`, `y`, `width` and `height`, as masks have.
- Polygons load everywhere other annotation details load, including video frames and export. They take `object_track_id`, as masks do.
- A migration adds the table and the enum value.
- **Evaluation** stays masks-only. Polygon sources get a clear error, for example "Polygon annotations are not yet supported for instance segmentation evaluation.", plus a changelog entry. COCO segmentation sources now fail with this error. Before, they "ran" with box-only masks that were silently skipped. *Not taken:* comparing polygons only with polygons. It still needs rasterizing or polygon geometry, and it can't handle the common case of polygon ground truth with mask predictions, or COCO's mixed ground truth.

## Follow-ups

- YouTube-VIS ingestion and export of polygons, with the same `annotation_task` deprecation. Labelformat already supports both.
- Rasterizing polygons, for evaluation in memory against polygons or masks (as COCOeval does), and optionally for polygon-to-mask export, including Pascal VOC. Labelformat's Pascal VOC writer already has a polygon rasterizer that could be reused.
- Remove the deprecated `annotation_type` and `to_coco_segmentation_masks`.
- Optional, in labelformat: its COCO reader decides the type by `iscrowd`, while pycocotools and Detectron2 check the data type. A file with RLE and `iscrowd=0` therefore fails in labelformat.

## Left to the builder

File, table and class names, except the public `AnnotationType.POLYGON`, `AnnotationTask`, `annotation_task` and the Python API names above. Also left: the `ExportFormat` values, the PR split, and test names.
