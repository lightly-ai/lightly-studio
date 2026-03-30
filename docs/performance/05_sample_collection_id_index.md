# 05 – Index on `SampleTable.collection_id`

## Problem description

### Field definition (before fix)

```python
# lightly_studio/src/lightly_studio/models/sample.py
class SampleBase(SQLModel):
    """Base class for the Sample model."""

    """The collection ID to which the sample belongs."""
    collection_id: UUID = Field(default=None, foreign_key="collection.collection_id")
```

`collection_id` was declared **without** `index=True`.  Every SQL query that
filters by this column therefore required a full sequential scan over the entire
`sample` table.

### How `SampleTable` grows with annotation proxy samples

`annotation_resolver.create_many()` creates a *proxy sample* in `SampleTable`
for every annotation it persists.  The proxy is stored in a child collection of
the parent dataset and is the canonical record that ties an annotation to the
rest of the system (tags, embeddings, captions, …).

For a dataset of **100 000 video frames** annotated with **10 labels per frame**:

| Entity                        | Rows added to `SampleTable` |
|-------------------------------|----------------------------:|
| Video frames                  |                     100 000 |
| Annotation proxy samples      |                   1 000 000 |
| **Total**                     |               **1 100 000** |

Every grid-page request calls `sample_resolver.get_filtered_samples()` with a
`SampleFilter(collection_id=…)`.  Without an index, each request scans all
~1.1 M rows even though only the ~100 k rows belonging to the requested
collection are relevant.

---

## Benchmark methodology

**Test file:**
`lightly_studio/tests/performance/test_sample_collection_id_index_benchmark.py`

**Setup:**

- In-memory DuckDB database (mirrors the development / test backend).
- 2 collections, each containing **2 000 images** → **4 000 rows** in
  `SampleTable` total.
- Bulk-inserted via `image_resolver.create_many()`.

**Measurement:**

1. One warm-up call (not counted).
2. `_NUM_RUNS = 5` timed calls to:

   ```python
   sample_resolver.get_filtered_samples(
       session=session,
       filters=SampleFilter(collection_id=target_collection_id),
   )
   ```

3. **Median** of the five wall-clock times reported.

Run the benchmark with:

```bash
uv run pytest tests/performance/test_sample_collection_id_index_benchmark.py -v -s
```

---

## Results

> **Note:** The benchmark uses an in-memory DuckDB database (the development
> backend).  DuckDB's columnar, vectorised engine already scans 4 000 rows very
> efficiently; the measured latency is dominated by Python/SQLAlchemy overhead
> rather than storage I/O.  The index's impact is most visible on the
> **PostgreSQL production backend** at ≥ 100 k rows — see the explanation below.

| State         | Min (ms) | Median (ms) | Max (ms) |
|---------------|:--------:|:-----------:|:--------:|
| Before (no index) | 20.50 | 20.59 | 22.51 |
| After (`index=True`) | 20.46 | 20.68 | 21.11 |

**Observed speedup (DuckDB, 4 000 rows):** ~1.0× — the latency is equivalent
at this scale, confirming that the bottleneck is not the scan itself.

### Why DuckDB shows a small delta at this scale

DuckDB is a columnar analytical engine that achieves very fast scans through
vectorised execution and compressed storage.  At 4 000 rows the baseline scan
is already sub-millisecond at the storage level; the measured time is dominated
by Python/SQLAlchemy overhead rather than the scan itself.

The benefit of the index becomes significant at **production scale** (≥ 100 k
rows, PostgreSQL backend):

- DuckDB's ART (Adaptive Radix Tree) index reduces I/O for larger datasets, but
  its scan performance is already excellent for moderate sizes.
- PostgreSQL uses a B-tree index and performs a **full table scan** by default
  when no index is present.  For 1.1 M rows and a selectivity of ~9 %
  (100 k / 1.1 M) an index scan is significantly faster than a sequential scan.

---

## Fix

**File:** `lightly_studio/src/lightly_studio/models/sample.py`

```diff
-    collection_id: UUID = Field(default=None, foreign_key="collection.collection_id")
+    collection_id: UUID = Field(
+        default=None, foreign_key="collection.collection_id", index=True
+    )
```

SQLModel passes `index=True` to SQLAlchemy, which generates a
`CREATE INDEX` statement for the column when the table is created.  Existing
deployments will pick up the index the next time `SQLModel.metadata.create_all()`
is called (or via a manual migration).
