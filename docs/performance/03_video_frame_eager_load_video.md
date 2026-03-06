# 03 – VideoFrame Eager-Load: `video` relationship

## Problem description

### Relevant code

#### `get_all_by_collection_id.py`

```python
# lightly_studio/src/lightly_studio/resolvers/video_frame_resolver/get_all_by_collection_id.py

def _get_load_options() -> LoaderOption:            # ← returned a single option
    """Eager-load annotations to avoid multiple queries."""
    return selectinload(VideoFrameTable.sample).options(
        selectinload(SampleTable.annotations).options(
            joinedload(AnnotationBaseTable.annotation_label),
            joinedload(AnnotationBaseTable.object_detection_details),
            joinedload(AnnotationBaseTable.segmentation_details),
            selectinload(AnnotationBaseTable.sample).options(selectinload(SampleTable.tags)),
        ),
    )
    # ↑ VideoFrameTable.video is NOT included here
```

The base query joins `VideoFrameTable` → `VideoTable` for `ORDER BY`, but
`_get_load_options()` only eager-loads the `sample` → `annotations` chain.
The `video` relationship is therefore resolved with the SQLModel/SQLAlchemy
default strategy **`lazy="select"`**.

#### `frame.py`

```python
# lightly_studio/src/lightly_studio/api/routes/api/frame.py

def _build_video_frame_view(vf: VideoFrameTable) -> VideoFrameView:
    return VideoFrameView(
        frame_number=vf.frame_number,
        frame_timestamp_s=vf.frame_timestamp_s,
        sample_id=vf.sample_id,
        video=_build_video_view(vf.video),   # ← lazy SELECT fires here
        sample=_build_sample_view(vf.sample),
    )
```

`vf.video` triggers a `SELECT video WHERE sample_id = ?` for every
`VideoFrameTable` row whose parent video has not yet been loaded into the
SQLAlchemy identity map.

### Lazy-load chain

```
GET /collections/{id}/frame/
  └─ get_all_by_collection_id()
       ├─ SELECT COUNT(*)              (1 query)
       ├─ SELECT video_frame …         (1 query, paginated)
       └─ for each frame in page:
            └─ vf.video               (1 query per unique video ← N+1)
```

### Worst-case query count

For a page of **100 frames** from **100 distinct videos** (e.g. 100 k
1-second clips):

| Phase | Queries |
|---|---|
| `SELECT COUNT(*)` | 1 |
| Main paginated `SELECT video_frame …` | 1 |
| `selectinload` for `VideoFrameTable.sample` | 1 |
| Lazy `SELECT video WHERE sample_id = ?` × 100 | **100** |
| **Total** | **103** |

---

## Benchmark methodology

File: `lightly_studio/tests/performance/test_video_frame_n1_benchmark.py`

1. Create an **in-memory DuckDB** session via `create_engine("duckdb:///:memory:")`.
2. Insert **20 distinct videos × 5 frames each = 100 frames** using helpers
   from `tests/resolvers/video/helpers.py`.
3. Attach a `before_cursor_execute` SQLAlchemy event listener to the engine to
   count every SQL statement issued.
4. Call `video_frame_resolver.get_all_by_collection_id()` for a page of
   100 frames.
5. Assert that the total `SELECT` count is **less than `NUM_VIDEOS` (20)**,
   proving the fix is in effect.

---

## Before / after numbers

| Metric | Before fix | After fix |
|---|---|---|
| SQL `SELECT` statements (20 videos, 100 frames) | ~24 | ~4–5 |
| Worst case (100 distinct videos, 100 frames) | ~103 | ~4–5 |
| N+1 scaling | O(N videos) | O(1) |

---

## Fix diff

```diff
--- a/lightly_studio/src/lightly_studio/resolvers/video_frame_resolver/get_all_by_collection_id.py
+++ b/lightly_studio/src/lightly_studio/resolvers/video_frame_resolver/get_all_by_collection_id.py
@@ -48,14 +48,17 @@
-    samples_query = base_query.options(_get_load_options()).order_by(
+    samples_query = base_query.options(*_get_load_options()).order_by(

-def _get_load_options() -> LoaderOption:
-    """Eager-load annotations to avoid multiple queries."""
-    return selectinload(VideoFrameTable.sample).options(
-        selectinload(SampleTable.annotations).options(
-            joinedload(AnnotationBaseTable.annotation_label),
-            joinedload(AnnotationBaseTable.object_detection_details),
-            joinedload(AnnotationBaseTable.segmentation_details),
-            selectinload(AnnotationBaseTable.sample).options(selectinload(SampleTable.tags)),
-        ),
-    )
+def _get_load_options() -> list[LoaderOption]:
+    """Eager-load video and annotations to avoid multiple queries."""
+    return [
+        selectinload(VideoFrameTable.video),
+        selectinload(VideoFrameTable.sample).options(
+            selectinload(SampleTable.annotations).options(
+                joinedload(AnnotationBaseTable.annotation_label),
+                joinedload(AnnotationBaseTable.object_detection_details),
+                joinedload(AnnotationBaseTable.segmentation_details),
+                selectinload(AnnotationBaseTable.sample).options(selectinload(SampleTable.tags)),
+            ),
+        ),
+    ]
```

### Why `selectinload` and not `joinedload`?

`joinedload` adds a `LEFT OUTER JOIN` to the main query.  Since `VideoTable`
rows are *already* joined for `ORDER BY`, a second `joinedload` join would
produce duplicate result rows.  `selectinload` fires a separate
`SELECT … WHERE sample_id IN (…)` after the main query – one round-trip for
*all* video IDs on the page, avoiding both the N+1 and the row-multiplication
problem.
