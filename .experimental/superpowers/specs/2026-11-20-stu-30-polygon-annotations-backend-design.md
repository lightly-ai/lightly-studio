# STU-30: Polygon Annotations (Backend)

## Why

Users need outlines for irregular objects. Boxes are too coarse, and pixel masks are tedious when an outline is enough. Also, today a COCO polygon added as `SEGMENTATION_MASK` becomes a mask annotation with only a box: the vertices are dropped.

## Scope

- A polygon annotation: one or more parts (closed loops), no holes, on images and video frames.
- Add polygons from COCO and YOLO, and export them to the same formats.
- Polygons can be queried by their bounding box, and cropped for embeddings on images. Crops on video frames aren't supported, the same as for masks today.
- The dropped-vertices bug is fixed for COCO.
- Backend only. It ships before the frontend, and until then the GUI can't show polygons. That gap is accepted. The one GUI change is the two export entries in the export dialog (see Export), so the new exports can be reached.
- One labelformat fix. 0.1.17 already reads and writes `MultiPolygon` for COCO and YOLO. But its YOLO segmentation reader crashes on images without a label file and on blank lines, both common in real datasets; its detection reader handles them. Fixing labelformat was chosen over a workaround in Studio, so other users get the fix too.

**Out of scope:** conversion between polygons and masks, holes, migrating existing masks (including the box-only ones), AI-assisted polygons, polygon evaluation, and YouTube-VIS polygons (see Ingestion).

**Changes to the issue's requirements:**
- Multipolygons from the start, not just simple polygons.
- No polygon-to-mask conversion on export.
- Two new export entries become one extended COCO export and one new YOLO export (see Export).

## Data model

**A new type.**
- `AnnotationType.POLYGON` (`"polygon"`) gets its own details table, linked one-to-one like the other types. Users see "polygon" and "part", never "multipolygon". The glossary gets both terms.
  - *Alternative considered:* a polygon field on the segmentation annotation. One type would have two shapes, every mask reader would have to branch, and a row could hold both or neither.

**Storage.** The details table holds two things per polygon:

| Column | Content |
|---|---|
| `polygons` | `JSON`: a list of parts, each a list of `[x, y]` vertices. Rounded to 0.001px. |
| `x`, `y`, `width`, `height` | Integer bounding box, computed from the vertices. |

For example, a polygon with a triangle and a square as its two parts:

```json
[[[10.5, 20], [30, 20], [30, 40.25]],
 [[50, 50], [60, 50], [60, 60], [50, 60]]]
```

*Why JSON:* the API and labelformat's `MultiPolygon.polygons` use the same nested lists, so no conversion code is needed.
- *Alternatives considered:*
  - Flat `float8[]` coordinate array plus a second array with where each part starts (offset). On PostgreSQL with 1M polygons it was only about 20% smaller and 15% faster to load. That doesn't pay for two columns that must stay in sync.
  - `JSONB`: nearly twice as large.
  - Nested PostgreSQL arrays: don't work, because PostgreSQL arrays must be rectangular and parts have different vertex counts.

*Vertices* are float pixels in the original image, with the origin at the top-left corner.
- Floats, not integers like boxes, so coordinates stay lossless through COCO and YOLO round trips. labelformat uses floats too.
- They are rounded to 0.001 px. This about halves the size and transfer of vertices drawn in the UI, and the lost precision can't be seen.

*Why also store a box:* crops, sorting, filters and the query language read the integer box, as they do for masks. It is computed on every write, rounded outward so it contains every vertex.
- *Alternative considered:* computing the box when it's read. That needs JSON unnesting written separately for DuckDB and PostgreSQL, and it can't be indexed.

*Size is fine:* transfer to the frontend is bounded by page size, about 1.3 MB per grid page even with 200 polygons per image.

**Validation.** Every write goes through one function, because the database doesn't check the shape. It requires at least 1 part, at least 3 vertices per part and finite numbers, then rounds and computes the box.

**Editing.** Every edit sends the full polygon: move, add or remove a vertex, or add or remove a part. The update replaces the polygon and recomputes the box, so no per-vertex endpoints are needed. A direct box edit on a polygon is rejected *(my call)*.

**Python API.** `PolygonAnnotation` and `CreatePolygon`, mirroring the mask classes *(my call)*.

## Ingestion

Today the COCO methods take `annotation_type` (`OBJECT_DETECTION` or `SEGMENTATION_MASK`) to choose what to read from the file. With polygons, one segmentation file gives two annotation types: polygons and masks. So an annotation type can no longer name the choice. A new public enum names what to read instead:

```python
class AnnotationFileTask(str, Enum):
    OBJECT_DETECTION = "object_detection"
    INSTANCE_SEGMENTATION = "instance_segmentation"
```

- **COCO** (`add_samples_from_coco`, `add_annotations_from_coco`): `annotation_task` defaults to `OBJECT_DETECTION`. With `INSTANCE_SEGMENTATION`, `iscrowd=0` entries become polygons and `iscrowd=1` entries become masks, so a mixed file like COCO 2017 comes in completely in one call.
- **YOLO** (`add_samples_from_yolo`, `add_annotations_from_yolo`): with `INSTANCE_SEGMENTATION`, each segmentation line becomes a single-part polygon.
- **Deprecation:** the old `annotation_type` on the COCO methods still works and raises a `DeprecationWarning`. `SEGMENTATION_MASK` maps to `INSTANCE_SEGMENTATION`. Passing both parameters raises `ValueError`. It is removed in a later minor release. Both the deprecation and the removal get changelog entries.
- **Invalid polygons:** parts with fewer than 3 vertices or with non-finite coordinates are dropped. An annotation with no valid parts is skipped, with one warning that gives the count. COCO 2017 has a few *(my call)*.
- **YouTube-VIS stays as it is.** It shares the segmentation helper with COCO, so COCO gets a new helper that creates polygons, and YouTube-VIS keeps the current one. Polygon frames in YouTube-VIS files still become box-only masks. Official YouTube-VIS data uses RLE masks, so this only affects polygon-based files.
  - *Alternative considered:* the same fix for YouTube-VIS. It also needs `annotation_task` on `add_videos_from_youtube_vis`, a polygon path in the YouTube-VIS export, and two labelformat writer fixes (polygon areas, track `iscrowd`), for a rare case.

## Export

- **"Segmentation masks (COCO)" becomes "Instance segmentation (COCO)".** It writes polygons as `iscrowd=0` and masks as RLE with `iscrowd=1` in one file, as the COCO spec pairs them. The docs note that COCOeval treats `iscrowd=1` as ignore regions; that is already true today.
  - *Alternative considered:* a separate polygons-only COCO export. A mixed dataset like COCO 2017 would lose its crowd masks on the way out.
- **New "Instance segmentation (YOLO)":** polygons only. YOLO has no mask encoding, so masks are skipped with a warning that gives the count. YOLO allows one polygon per object, so labelformat joins the parts with zero-width bridges, and a multi-part polygon comes back as one part.
- **Pascal VOC stays masks-only.** It shares the COCO export's annotation input, and labelformat's Pascal VOC writer already rasterizes polygons, so including polygons would quietly convert them to masks. That conversion is out of scope; the follow-up can reuse this labelformat code.
- **YouTube-VIS stays masks-only.** Polygons on video frames, added through the API or Python, are left out of it.
- **Python:** `to_coco_instance_segmentation` and `to_yolo_instance_segmentation`. `to_coco_segmentation_masks` is deprecated like `annotation_type` *(my call)*.

## Other changes

- The query language and the Python query API get polygon `x`, `y`, `width` and `height`, as masks have. The query editor's `polygon(...)` keyword is part of the frontend work.
- Polygons load everywhere other annotation details load, including video frames and export. They take `object_track_id`, as masks do.
- A migration adds the table and the enum value.
- **Evaluation** stays masks-only. Polygon sources get a clear error, for example "Polygon annotations are not yet supported for instance segmentation evaluation.", plus a changelog entry. COCO segmentation sources now fail with this error. Before, they "ran" with box-only masks that were silently skipped.
  - *Alternative considered:* comparing polygons only with polygons. It still needs rasterizing or polygon geometry, and it can't handle the common case of polygon ground truth with mask predictions, or COCO's mixed ground truth.

## Follow-ups

- Rasterizing polygons, for evaluation in memory against polygons or masks (as COCOeval does), and optionally for polygon-to-mask export, including Pascal VOC. Labelformat's Pascal VOC writer already has a polygon rasterizer that could be reused.
- Remove the deprecated `annotation_type` and `to_coco_segmentation_masks`.
- YouTube-VIS polygons: ingestion with `annotation_task`, export, and labelformat's YouTube-VIS writer, which writes no area for polygon frames and takes a track's `iscrowd` from its last frame.
- Optional, in labelformat: its COCO reader decides the type by `iscrowd`, while pycocotools and Detectron2 check the data type. A file with RLE and `iscrowd=0` therefore fails in labelformat.

## Left to the builder

File, table and class names, except the public `AnnotationType.POLYGON`, `AnnotationFileTask`, `annotation_task` and the Python API names above. Also left: the `ExportFormat` values, the PR split, and test names.
