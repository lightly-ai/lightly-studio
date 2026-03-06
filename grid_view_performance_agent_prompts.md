# Grid View Performance Optimization – Agent Prompts

Each section below is a self-contained prompt you can paste into a fresh agentic session.
The agent is expected to:
1. Describe the problem with code references
2. Implement a micro-benchmark that reproduces the slow path
3. Implement the fix
4. Re-run the benchmark to measure the improvement
5. Write everything (problem, benchmark, fix, numbers) into a `.md` file inside the repo

---

## Candidate 1 – Missing DB indexes on `AnnotationBaseTable`

```
You are working on the repository at /home/runner/work/lightly-studio/lightly-studio.

### Task
Profile and fix a missing-index performance problem in the backend, then document everything
in a new file docs/performance/01_annotation_indexes.md.

### Background
The grid view for a dataset with 100 k video frames and 10 annotations per frame is slow.
A likely cause is that two heavily-queried foreign-key columns on `AnnotationBaseTable` have
no database index, forcing full table scans on every filter or join.

Relevant file:
  lightly_studio/src/lightly_studio/models/annotation/annotation_base.py

The two unindexed columns are:
  annotation_label_id: UUID = Field(foreign_key="annotation_label.annotation_label_id")
  parent_sample_id:    UUID = Field(foreign_key="sample.sample_id")

### Steps you must perform

1. **Describe the problem** – show the current field definitions and explain why the missing
   `index=True` is a bottleneck for annotation filtering and join queries at scale.

2. **Implement a benchmark** – write a pytest benchmark in
   `lightly_studio/tests/performance/test_annotation_index_benchmark.py` that:
   - Creates an in-memory DuckDB session (reuse the `test_db` fixture pattern from
     `tests/helpers_resolvers.py`)
   - Inserts 10 000 annotations across 1 000 images (10 annotations per image) using
     `annotation_resolver.create_many`
   - Measures the wall-clock time of `annotation_resolver.get_all()` filtered by
     `collection_id` (via `AnnotationsFilter`) and by `annotation_label_id`
   - Runs each query 5 times and records the median time
   - Prints/asserts a baseline timing for the unindexed state

3. **Implement the fix** – add `index=True` to both fields in `annotation_base.py`.

4. **Re-run the benchmark** – capture the new timings and compute the speedup ratio.

5. **Write the report** – create `docs/performance/01_annotation_indexes.md` with:
   - Problem description with file/line references
   - Benchmark methodology
   - Before / after timing table
   - The diff of the fix

Run the project's linter (`ruff check` and `ruff format --check` from the
`lightly_studio/` directory) on every file you touch and fix any issues.
Make sure all pre-existing tests still pass by running
`python -m pytest tests/ -x -q --timeout=120` from `lightly_studio/`.
```

---

## Candidate 2 – `AnnotationsFilter` tag filter: JOIN + DISTINCT → subquery

```
You are working on the repository at /home/runner/work/lightly-studio/lightly-studio.

### Task
Profile and fix an inefficient tag-filter query in the annotations resolver, then document
everything in a new file docs/performance/02_annotation_tag_filter_subquery.md.

### Background
The annotations grid view calls `GET /collections/{id}/annotations/payload` with optional
`tag_ids` query parameters.  The current implementation of `AnnotationsFilter.apply()` in

  lightly_studio/src/lightly_studio/resolvers/annotations/annotations_filter.py

handles tag filtering with a JOIN + DISTINCT:

  query = (
      query.join(annotation_sample.tags)
      .where(annotation_sample.tags.any(col(TagTable.tag_id).in_(self.tag_ids)))
      .distinct()
  )

For large annotation tables this explodes the intermediate result set before DISTINCT
collapses it, making every tag-filtered page very slow.

The fix is to replace it with a correlated IN-subquery identical to the pattern already
used in `SampleFilter._apply_tag_filters()` in
`lightly_studio/src/lightly_studio/resolvers/sample_resolver/sample_filter.py`.

### Steps you must perform

1. **Describe the problem** – show the current code, explain why JOIN+DISTINCT is slow at
   scale, and show the existing subquery pattern in `SampleFilter` as the reference fix.

2. **Implement a benchmark** – write a pytest benchmark in
   `lightly_studio/tests/performance/test_annotation_tag_filter_benchmark.py` that:
   - Creates an in-memory DuckDB session
   - Inserts 5 000 annotations tagged with one of two tags
   - Measures wall-clock time of `annotation_resolver.get_all()` with
     `AnnotationsFilter(tag_ids=[tag_id])` for the BEFORE state (JOIN+DISTINCT)
   - Runs the query 5 times, records median

3. **Implement the fix** – in `annotations_filter.py` replace the JOIN+DISTINCT block with:

   sample_ids_with_tags = (
       select(SampleTable.sample_id)
       .join(SampleTable.tags)
       .where(col(TagTable.tag_id).in_(self.tag_ids))
       .distinct()
   )
   query = query.where(col(annotation_sample.sample_id).in_(sample_ids_with_tags))

   Also add `from sqlmodel import col, select` if `select` is not yet imported.

4. **Re-run the benchmark** – capture the new timings and compute the speedup ratio.

5. **Write the report** – create `docs/performance/02_annotation_tag_filter_subquery.md`
   with problem description, benchmark methodology, before/after table, and the fix diff.

Run the project's linter on every file you touch.
Make sure all pre-existing tests still pass:
`python -m pytest tests/ -x -q --timeout=120` from `lightly_studio/`.
```

---

## Candidate 3 – N+1 video loading in the video frame grid endpoint

```
You are working on the repository at /home/runner/work/lightly-studio/lightly-studio.

### Task
Profile and fix an N+1 query problem for the `VideoTable` relationship in the video frame
grid endpoint, then document everything in
docs/performance/03_video_frame_eager_load_video.md.

### Background
The frame grid endpoint `POST /collections/{id}/frame/` returns pages of `VideoFrameView`
objects.  The resolver in

  lightly_studio/src/lightly_studio/resolvers/video_frame_resolver/get_all_by_collection_id.py

builds the base query with a SQL JOIN on VideoTable (for ORDER BY), but `_get_load_options()`
does NOT include any loading strategy for `VideoFrameTable.video`.  The relationship is
defined with the SQLModel default lazy="select", so every call to `vf.video` inside
`_build_video_frame_view()` in
  lightly_studio/src/lightly_studio/api/routes/api/frame.py
triggers a separate SELECT – one per unique video in the page.

For a dataset with one video per frame (e.g. 100 k 1-second clips) this becomes a true N+1.

### Steps you must perform

1. **Describe the problem** – show the relevant code in `get_all_by_collection_id.py` and
   `frame.py`, explain the lazy-load chain, and give a worst-case query count estimate for
   a page of 100 frames from 100 distinct videos.

2. **Implement a benchmark** – write a pytest benchmark in
   `lightly_studio/tests/performance/test_video_frame_n1_benchmark.py` that:
   - Creates an in-memory DuckDB session
   - Inserts 20 distinct videos with 5 frames each (100 frames total) using helpers from
     `tests/resolvers/video/helpers.py`
   - Patches SQLAlchemy to count SELECT statements (or simply measures wall-clock time)
   - Calls `video_frame_resolver.get_all_by_collection_id()` for a page of 100 frames and
     records number of DB round-trips / wall-clock time for the BEFORE state

3. **Implement the fix** – in `get_all_by_collection_id.py`:
   - Change `_get_load_options()` to return `list[LoaderOption]`
   - Append `selectinload(VideoFrameTable.video)` to the list
   - Update the call site from `.options(_get_load_options())` to
     `.options(*_get_load_options())`

4. **Re-run the benchmark** – show the reduced query count / faster wall-clock time.

5. **Write the report** – create `docs/performance/03_video_frame_eager_load_video.md`
   with problem description, benchmark methodology, before/after numbers, and the fix diff.

Run the project's linter on every file you touch.
Make sure all pre-existing tests still pass:
`python -m pytest tests/ -x -q --timeout=120` from `lightly_studio/`.
```

---

## Candidate 4 – N+1 annotation relationship loading in `get_all_with_payload`

```
You are working on the repository at /home/runner/work/lightly-studio/lightly-studio.

### Task
Profile and fix multiple N+1 query problems inside `get_all_with_payload` in the
annotations payload resolver, then document everything in
docs/performance/04_annotation_payload_eager_load.md.

### Background
The annotations grid calls `GET /collections/{id}/annotations/payload` which is handled by

  lightly_studio/src/lightly_studio/resolvers/annotation_resolver/get_all_with_payload.py

`_build_base_query()` returns a SELECT over `(AnnotationBaseTable, ImageTable|VideoFrameTable)`
but provides `.options()` only for the *payload* side (ImageTable / VideoFrameTable).
No load strategies are set for the AnnotationBaseTable relationships.

`AnnotationView.from_annotation_table()` (defined in
  lightly_studio/src/lightly_studio/models/annotation/annotation_base.py)
then accesses these lazy relationships synchronously inside the list comprehension:

  annotation.annotation_label.annotation_label_name   → lazy "select" per unique label
  annotation.object_detection_details                  → lazy "select" per annotation
  annotation.segmentation_details                      → lazy "select" per annotation
  annotation.sample.tags                               → lazy "select" per annotation sample

For a page of 100 annotations this produces up to ~300 extra SELECT statements.

### Steps you must perform

1. **Describe the problem** – show the relevant code sections, list which relationships are
   lazy-loaded, and give a worst-case query count for a page of 100 annotations with
   100 distinct labels.

2. **Implement a benchmark** – write a pytest benchmark in
   `lightly_studio/tests/performance/test_annotation_payload_n1_benchmark.py` that:
   - Creates an in-memory DuckDB session
   - Inserts 100 images each with 1 annotation (using `annotation_resolver.create_many`)
     using 10 distinct labels
   - Counts SQLAlchemy SELECT events using the `event.listen(engine, "before_cursor_execute")`
     pattern, OR measures wall-clock time
   - Calls `annotation_resolver.get_all_with_payload()` for a page of 100 annotations
     and records the SELECT count / time for the BEFORE state

3. **Implement the fix** – in `get_all_with_payload.py`, add the following options to
   `_build_base_query()` for **both** the IMAGE branch and the VIDEO_FRAME branch:

   joinedload(AnnotationBaseTable.annotation_label),
   joinedload(AnnotationBaseTable.object_detection_details),
   joinedload(AnnotationBaseTable.segmentation_details),
   selectinload(AnnotationBaseTable.sample).options(
       selectinload(SampleTable.tags),
   ),

   Also add `selectinload` to the `from sqlalchemy.orm import ...` line.

4. **Re-run the benchmark** – show the reduced SELECT count / faster wall-clock time.

5. **Write the report** – create `docs/performance/04_annotation_payload_eager_load.md`
   with problem description, benchmark methodology, before/after numbers, and the fix diff.

Run the project's linter on every file you touch.
Make sure all pre-existing tests still pass:
`python -m pytest tests/ -x -q --timeout=120` from `lightly_studio/`.
```

---

## Candidate 5 – Missing index on `SampleBase.collection_id`

```
You are working on the repository at /home/runner/work/lightly-studio/lightly-studio.

### Task
Profile and fix a missing-index problem on the `SampleTable.collection_id` column, then
document everything in docs/performance/05_sample_collection_id_index.md.

### Background
`SampleTable` stores rows for every entity in the system: images, video frames, and the
per-annotation proxy samples created by `annotation_resolver.create_many()`.  For a dataset
with 100 k video frames and 10 annotations each, `SampleTable` contains ~1.1 million rows.

`SampleBase.collection_id` is the primary filter used by almost every grid endpoint, yet
the column is declared without `index=True`:

  # lightly_studio/src/lightly_studio/models/sample.py
  class SampleBase(SQLModel):
      collection_id: UUID = Field(default=None, foreign_key="collection.collection_id")

Every WHERE clause on `collection_id` therefore requires a full table scan over >1 M rows.

### Steps you must perform

1. **Describe the problem** – show the field definition, explain how `SampleTable` grows
   with annotation proxy samples, and estimate the table size for a 100 k frame dataset.

2. **Implement a benchmark** – write a pytest benchmark in
   `lightly_studio/tests/performance/test_sample_collection_id_index_benchmark.py` that:
   - Creates an in-memory DuckDB session
   - Inserts 2 collections, each with 2 000 images (4 000 rows total in SampleTable)
   - Measures wall-clock time of `sample_resolver.get_filtered_samples()` filtered by
     `collection_id` (via `SampleFilter`) for the BEFORE (unindexed) state
   - Runs the query 5 times, records median

3. **Implement the fix** – add `index=True` to `collection_id` in `SampleBase`:

   collection_id: UUID = Field(
       default=None, foreign_key="collection.collection_id", index=True
   )

4. **Re-run the benchmark** – capture the new timings and compute the speedup ratio.

5. **Write the report** – create `docs/performance/05_sample_collection_id_index.md`
   with problem description, benchmark methodology, before/after table, and the fix diff.

Run the project's linter on every file you touch.
Make sure all pre-existing tests still pass:
`python -m pytest tests/ -x -q --timeout=120` from `lightly_studio/`.
```
