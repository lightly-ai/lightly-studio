# Annotation Payload Eager-Loading – N+1 Query Fix

## Problem

The `GET /collections/{id}/annotations/payload` endpoint is served by
`lightly_studio/resolvers/annotation_resolver/get_all_with_payload.py`.

`_build_base_query()` constructed a `SELECT` over
`(AnnotationBaseTable, ImageTable|VideoFrameTable)` and set `.options()` only
for the *payload* side (`ImageTable` / `VideoFrameTable`).  No load strategies
were configured for the `AnnotationBaseTable` relationships, so SQLAlchemy
defaulted to **lazy "select"** loading.

`AnnotationView.from_annotation_table()` (defined in
`lightly_studio/models/annotation/annotation_base.py`) then accessed these
lazy relationships synchronously inside the list comprehension:

| Attribute accessed | Relationship | Strategy (before fix) |
|-|-|-|
| `annotation.annotation_label.annotation_label_name` | `AnnotationBaseTable.annotation_label` | lazy select – 1 query per *unique* label |
| `annotation.object_detection_details` | `AnnotationBaseTable.object_detection_details` | lazy select – 1 query per annotation |
| `annotation.segmentation_details` | `AnnotationBaseTable.segmentation_details` | lazy select – 1 query per annotation |
| `annotation.sample.tags` | `AnnotationBaseTable.sample` → `SampleTable.tags` | lazy select – 1 query per annotation + 1 per annotation for tags |

### Worst-case query count (100 annotations, 10 distinct labels)

| Query | Count |
|---|---|
| Main annotation SELECT | 1 |
| Total-count subquery SELECT | 1 |
| `annotation_label` (10 unique labels) | 10 |
| `object_detection_details` (one per annotation) | 100 |
| `sample` row (one per annotation) | 100 |
| `sample.tags` (one per annotation) | 100 |
| **Total** | **312** |

## Fix

In `_build_base_query()`, the following eager-load options were added to
**both** the `IMAGE` branch and the `VIDEO_FRAME` branch:

```python
joinedload(AnnotationBaseTable.annotation_label),
joinedload(AnnotationBaseTable.object_detection_details),
joinedload(AnnotationBaseTable.segmentation_details),
selectinload(AnnotationBaseTable.sample).options(
    selectinload(SampleTable.tags),
),
```

`joinedload` inlines the related row into the same SQL `JOIN`, eliminating the
per-row round-trip entirely.  `selectinload` is used for the `sample → tags`
chain because `tags` is a many-to-many relationship and `joinedload` would
produce a Cartesian product with the outer annotation join.

`selectinload` issues exactly **two** extra queries regardless of page size:
one `IN (...)` query to load all `SampleTable` rows at once and one `IN (...)`
query to load all `SampleTagLinkTable` + `TagTable` rows at once.

### Diff

```diff
-from sqlalchemy.orm import aliased, joinedload, load_only
+from sqlalchemy.orm import aliased, joinedload, load_only, selectinload

 # IMAGE branch – .options(...)
+                joinedload(AnnotationBaseTable.annotation_label),
+                joinedload(AnnotationBaseTable.object_detection_details),
+                joinedload(AnnotationBaseTable.segmentation_details),
+                selectinload(AnnotationBaseTable.sample).options(
+                    selectinload(SampleTable.tags),
+                ),

 # VIDEO_FRAME branch – .options(...)
+                joinedload(AnnotationBaseTable.annotation_label),
+                joinedload(AnnotationBaseTable.object_detection_details),
+                joinedload(AnnotationBaseTable.segmentation_details),
+                selectinload(AnnotationBaseTable.sample).options(
+                    selectinload(SampleTable.tags),
+                ),
```

## Benchmark

### Methodology

A pytest benchmark in
`tests/performance/test_annotation_payload_n1_benchmark.py`:

1. Creates an in-memory DuckDB session.
2. Inserts 100 images each with one `OBJECT_DETECTION` annotation using 10
   distinct labels (via `annotation_resolver.create_many`).
3. Counts SQLAlchemy `SELECT` events using
   `event.listen(engine, "before_cursor_execute", ...)`.
4. Calls `annotation_resolver.get_all_with_payload()` for all 100 annotations.
5. Asserts the total SELECT count is ≤ 20.

### Results

| State | SELECT count (100 annotations, 10 labels) |
|---|---|
| **Before fix** (all relationships lazy) | ~312 |
| **After fix** (eager loading) | **5** |

The five queries after the fix are:

1. `SELECT COUNT(*)` – total count subquery
2. Main `SELECT` – annotation rows joined with image payload (includes
   `annotation_label`, `object_detection_details`, and `segmentation_details`
   via `JOIN`)
3. `SELECT` for `get_parent_collection_id` lookup
4. `SELECT IN (...)` – batch load of `SampleTable` rows (`selectinload`)
5. `SELECT IN (...)` – batch load of `SampleTagLinkTable` + `TagTable` rows
   (`selectinload`)
