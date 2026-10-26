# Embedding recompute: design

Date: 2026-10-23. Status: approved. Amended 2026-10-26 after a review of the PR stack, see
"Review decisions".

## Goal

Let a Python user fill the embedding gaps in an image dataset with one call:

1. Images that have no embedding, for example a dataset added with `embed=False`.
2. Annotations that have no embedding, for example annotations created in the GUI.
3. Annotations whose embedding is stale because their box was edited after embedding.

Success: after `dataset.compute_embeddings`, every image and every croppable annotation of the
dataset has an embedding of the default model, and every crop embedding matches the current box.

## Scope

In scope:

- Image datasets: images and annotation crops (object detection and segmentation masks).
- A public Python API. No GUI trigger, no background job.
- The default embedding model of each collection.

Out of scope, with the extension point this design keeps open:

| Out of scope | Extension point |
|---|---|
| Choosing another model, model switching | Internals take `embedding_model_id`. The public parameter will be `embedding_model_name`, as on `compute_typicality_metadata` (core/dataset.py:142). |
| Videos, frames, MCAP sequences | Each type gets its own fill in the same embed/ module. Video needs `embed_frames`, not `embed_annotations`. |
| Detecting image files changed on disk | `source_fingerprint` with a new prefix, for example `file1:<size>,<mtime>`. |
| GUI trigger | A future job calls the same embed/ function. |
| GUI indicator for annotations without an embedding | Reuse the private selection clause for a count. |
| 2D projection that recomputes only on request | Key the projection on the sample ID and source fingerprint of each row. See "Plot". |
| Scale to 100M samples | Covering index, see "Postgres risk". |

## Current state

- Embeddings are computed only inside `add_*` on `ImageDataset`. No public API, CLI or endpoint
  computes them later.
- `_generate_embeddings_image` (core/image/image_dataset.py:868-878) embeds all images without an
  embedding, but only when the collection already has a default model. On a dataset added with
  `embed=False` it embeds nothing.
- `embed_annotation_collection` (embed/embed_samples.py:181) embeds annotations without an
  embedding. Nothing re-embeds an annotation after its box changes.
- Both missing queries use a `NOT IN` subquery:
  resolvers/image_resolver/get_unembedded_sample_ids.py:29-36 and
  resolvers/annotation_resolver/get_unembedded_annotation_ids.py:39-48. On Postgres 18 this is
  quadratic once the subquery no longer fits in `hash_mem` (about 200k rows at default settings).
- Embedding rows are insert-only: `create_many` skips conflicts (`insert_ignoring_conflicts`).
  There is no upsert helper.
- Crops are built only from the annotation's integer `x, y, width, height`
  (resolvers/annotation_resolver/get_annotation_crops.py:75-90), for object detection and
  segmentation alike. Mask pixels, padding and EXIF are not used. `AnnotationCrop` carries only the
  box clamped to the image.

## Design

### 1. Public API

```python
class ImageDataset:
    def compute_embeddings(
        self,
        embed_annotations: bool = True,
        recompute_annotations: bool = False,
    ) -> None:
        """Embeds images and annotation crops that have no embedding or a stale one."""
```

- Images: embed every image without an embedding of the default model.
- Annotations, if `embed_annotations`: in every annotation collection of the dataset, embed crops
  that are missing or stale.
- `recompute_annotations=True`: re-embed every crop. This covers rows from before this change
  (no fingerprint) and a custom embedder that changed under the same name.
- Stale detection lands in PR 4 (see "PR split"). Until then the default call fills missing crops
  only, and `recompute_annotations=True` is the way to refresh edited boxes.
- Returns nothing and logs counts, like `add_*` and `compute_typicality_metadata`.
- The method on `ImageDataset` is a thin wrapper. The orchestration lives in a new module,
  embed/embed_dataset.py (`embed_samples.py` is 505 lines, over the 400-line limit).
- It never recomputes the 2D projection.

### 2. Schema

Add one nullable column to `sample_embedding` (models/sample_embedding.py):

```python
source_fingerprint: str | None = None
```

- Postgres: an Alembic revision that adds the column. Adding a nullable column without a default
  is a catalog-only change. It takes an `ACCESS EXCLUSIVE` lock briefly, so the revision sets
  `lock_timeout`.
- DuckDB: no migration. The CHANGELOG gets a BREAKING entry telling DuckDB users to re-index, as
  for earlier schema changes.
- Image rows store `None` in v1.

### 3. Fingerprint

Format, defined once as a SQL expression next to the crop query:

```sql
'bbox1:' || CAST(x AS VARCHAR) || ',' || CAST(y AS VARCHAR) || ','
         || CAST(width AS VARCHAR) || ',' || CAST(height AS VARCHAR)
```

- The raw, unclamped box. The columns are `INTEGER NOT NULL` on both backends, and both format
  integers the same way.
- `bbox1:` names the crop recipe. A future recipe change (padding, masked crops) bumps the prefix,
  so every crop becomes stale on the next `compute_embeddings`.
- The model is not part of the fingerprint. The row's primary key already includes it.

### 4. Write path

1. The crop query in `get_annotation_crops.py` selects the fingerprint expression in the same
   `SELECT` that reads the box.
2. `AnnotationCrop` gets a `source_fingerprint: str` field.
3. The crop writer stores that value verbatim with the vector.

Because the stored fingerprint comes from the read that built the crop, a box edit during a run
leaves a mismatch, and the next run re-embeds that crop.

Crop rows are written with a new upsert helper in database/db_insert.py:

```sql
ON CONFLICT (sample_id, embedding_model_id) DO UPDATE SET embedding, source_fingerprint
```

The selection returns unique IDs, so no statement holds the same key twice (Postgres rejects that).
`create_many` keeps first-writer-wins for every other caller: it skips conflicts so that two
concurrent `add_*` calls do not fail on Postgres (#2604).

`embedding_storage.store_embeddings` is the one storage entry point. It takes optional
`source_fingerprints` and a `replace` flag, and calls `create_many` or the upsert with a plain
`if`.

### 5. Selection

Extend `get_unembedded_annotation_ids` in place:

```sql
SELECT a.sample_id
FROM annotation_base a
JOIN sample s ON ...
JOIN image i ON ...
JOIN <detail table> d ON ...
LEFT JOIN sample_embedding e
  ON e.sample_id = a.sample_id AND e.embedding_model_id = :model_id
WHERE s.collection_id = :annotation_collection_id
  AND a.annotation_type IN (<croppable types>)
  AND (
    e.sample_id IS NULL                                  -- missing
    OR e.source_fingerprint <> <fingerprint expr>        -- stale
  )
ORDER BY i.file_path_abs
```

- `recompute_annotations=True` drops the gap condition and selects every croppable
  annotation.
- `<>` treats a `NULL` fingerprint as not stale. Legacy rows are re-embedded only through
  `recompute_annotations=True`.
- The stale condition lives in one private clause, so a future GUI count can reuse it.
- `get_unembedded_sample_ids` for images gets the same `LEFT JOIN` rewrite.

### 6. `add_*` behavior

`add_*` uses the same missing-or-stale selection as `compute_embeddings`, for the annotation source
it adds to. There is one selection, no `include_stale` flag. The extra work is bounded by the
number of edited boxes in that source, not by the dataset size, and the stale query costs at most
1.1x the missing one (see "Postgres risk").

### 7. Fixes on the shared path

1. Image fill resolves the default model first, then selects. A dataset with no default model gets
   all its images embedded, and its default is registered on the first embed.
2. Image IDs and paths are fetched per chunk. `embed_image_samples` loads every image row up front
   today (embed/embed_samples.py:151-156): 1.86 GiB of Python memory at 1M images.
3. Images are embedded before annotation crops, so a never-embedded annotation collection takes the
   parent's embedding space.
4. Annotation collections with no croppable annotations are skipped before the embedder is resolved.
   Today, resolving registers a default model, which turns on search and the plot in the GUI for a
   classification-only collection with no vectors.

### 8. Errors

- No usable embedder: `compute_embeddings` raises a new `NoUsableEmbedderError` in embed/errors.py. Today
  `resolve_default_embedder` logs a warning and returns `None` (embed/default_embedder.py:71),
  which would make the public call a silent no-op.
- A chunk where every file fails (`AllInputFilesFailedError`, embed/image_crop_embedding.py:154):
  `compute_embeddings` logs it and continues with the next chunk. Without this, one moved folder
  blocks every rerun, because committed chunks drop out of the selection and the failing chunk comes
  first again. If at least one chunk failed and nothing was stored, `compute_embeddings` raises
  `AllInputFilesFailedError` at the end, so a run where nothing worked is not silent. `add_*` keeps
  raising on the first failed chunk.
- A crop that fails to re-embed keeps its old vector and stays selected as stale.

### 9. Concurrency

Not fixed in v1, documented. The Python API shares one session with GUI requests when the GUI runs
in the same process (`start_gui_background`). A GUI commit or delete during a long run can fail a
chunk. `add_*` has the same risk today. A real fix needs a short-lived session per chunk.

### 10. Plot

Re-embedding marks the saved embedding plots of the model dirty: the upsert path calls
`embedding_plot_resolver.mark_dirty`, as `create_many` does since #2936. A re-embedded vector has a new first float, so today's 2D cache key
(`get_hash_by_collection_id`) changes and the next plot open recomputes
PaCMAP once per `compute_embeddings` run. The future on-request projection should key on
the sample ID and source fingerprint of each row, which catches replaced vectors without reading them.

### 11. Docs and CHANGELOG

- lightly_studio/docs/docs/workflows/embeddings.md:52-54: replace "Support for this is planned"
  with `compute_embeddings`.
- Document that re-embedding does not refresh typicality metadata, similarity metadata, or an active
  lasso region on the plot, and that the GUI should not be used to edit while a run is going.
- Document storage growth: on DuckDB a re-embed rewrites the row, about 3.3 KB per 512-dim row, and
  `CHECKPOINT` does not reclaim it.
- CHANGELOG: `Added` entry for `compute_embeddings`, BREAKING entry for the DuckDB re-index.

## Postgres risk

Unverified: the missing check can run on the primary key index alone, but the fingerprint compare
reads `sample_embedding` heap rows. If the vector is stored out of line in TOAST (likely for 512
dims, about 2 KB), heap rows are narrow and the scan is cheap. If it is inline (smaller models),
the scan reads every vector, about 20 GB at 10M rows.

PR 3 measures the stale query on Postgres with 10M annotations. If it is slow, a follow-up revision
adds a covering index:

```sql
CREATE INDEX ... ON sample_embedding (embedding_model_id, sample_id) INCLUDE (source_fingerprint);
```

Measured on #2929 (Postgres, 10M annotations, 1% missing, 1% stale, `EXPLAIN ANALYZE`): missing
only 5.3-5.7 s warm, missing or stale 5.4-5.9 s warm. The stale query is at most 1.1x, under the
2x limit, so the covering index is not added.

## Testing

Resolver, one test per branch, box values in the test body (style of
tests/resolvers/annotations/test_get_unembedded_annotation_ids.py):

- missing → selected
- fingerprint matches → not selected
- box edited → selected
- `NULL` fingerprint → not selected

Round trip on both backends (`pytest --postgres`):

- Embed a crop with negative `x`, so the clamped crop differs from the raw box. The selection is
  empty. Call `update_bounding_box`. The selection returns it. This locks the writer and the SQL
  expression together without asserting the format.

Race:

- A test embedder (like `_BoxXImageCropEmbedder`, tests/embed/test_embed_samples.py:100) edits the
  box inside `embed_image_crops`. The stored vector has the old `x`, and the annotation is selected
  as stale afterwards.

`compute_embeddings`:

- A dataset added with `embed=False` gets image and crop embeddings.
- An edited box gets a new vector. An unedited one keeps its vector.
- `recompute_annotations=True` re-embeds a crop that has no fingerprint. The default does not.
- No usable embedder raises.
- A chunk where all files fail is logged and the next chunk is embedded.
- `add_*` after a box edit re-embeds the edited crop of that annotation source.
- Every chunk fails → `compute_embeddings` raises `AllInputFilesFailedError`.

## PR split

The public API ships before the only breaking change. PRs 1 and 2 need no schema change.

1. Image fill fix: resolve the model first, `LEFT JOIN` in both missing queries, chunked fetch.
   CHANGELOG `Changed`: the first `add_*` with `embed=True` on a dataset added with `embed=False`
   now embeds the earlier images too.
2. `compute_embeddings` on ImageDataset, in embed/embed_dataset.py. Fills missing images and
   crops. `recompute_annotations=True` re-embeds every crop through the new upsert helper. Error
   handling, docs, CHANGELOG `Added`.
3. Store the crop fingerprint: column, Postgres revision, BREAKING CHANGELOG entry, fingerprint
   selected with the crop and written with the vector, race test. The PR title starts with
   `BREAKING:`, as the CHANGELOG entries do, for example
   `BREAKING: Store the crop fingerprint with annotation embeddings`.
4. Missing-or-stale selection, tests on both backends, Postgres 10M measurement.
   `compute_embeddings` picks up edited boxes by default. CHANGELOG `Changed`.

## Review decisions (2026-10-26)

A review of the PR stack (#2926-#2929) against this spec, with a second reviewer who did not read
the spec, gave these decisions:

1. Stale detection keeps the fingerprint column. Deleting the crop embedding on a box edit was the
   alternative. Two code paths edit a box (`annotation_resolver.update_bounding_box` and the
   `DBField` setters of the annotation classes), and a third would silently skip the delete. Also a
   deleted embedding drops the annotation from the plot and from similarity search, and the GUI has
   no way to recompute it. The DuckDB re-index is the usual cost of a schema change.
2. One selection, missing or stale, in `add_*` and `compute_embeddings`. See section 6.
3. `compute_embeddings` keeps both parameters. `embed_annotations` matches the `embed_annotations`
   flag of every `add_*` method. `recompute_annotations` is the only way to refresh embeddings
   from before the fingerprint, because a `NULL` fingerprint is not stale.
4. `add_*` with `embed=True` and no default model embeds every image without an embedding, as main
   already does when a default model exists (section 7.1).
5. Code quality, no behavior change:
   - One `store_embeddings` with a `replace` flag. It replaces `replace_embeddings` and the
     `_write_embeddings` helper that takes the write function as a `Callable`.
   - The crop embedding move from `embed_samples.py` to `embed_dataset.py` is its own commit,
     with no change to the moved code. The rewrite follows in a second commit.
   - Images and crops share one chunk loop in `embed_dataset.py` (progress bar, skip of a failed
     chunk, count).
   - `get_unembedded_annotation_ids.py` imports `build_croppable_annotations_query` from its
     module, not from its own package, and the query leaves the public `__all__`.
   - Tests: the selection branches are tested once, at the resolver level.
     `test_image_dataset__compute_embeddings.py` keeps 3-4 end-to-end tests for the wiring. Target:
     about 600 fewer test lines across `test_embed_dataset.py` and that file.
