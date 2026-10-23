# Embedding recompute: design

Date: 2026-10-23. Status: approved in brainstorming, pending spec review.

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
`create_many` keeps first-writer-wins for every other caller.

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
    OR (:include_stale AND e.source_fingerprint <> <fingerprint expr>)  -- stale
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

`add_*` keeps filling missing embeddings only (`include_stale=False`). Stale crops are refreshed
only by `compute_embeddings`. This keeps the cost of an ingest call bounded: adding 100 annotations
never re-embeds the 50k crops someone edited earlier.

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
  first again. `add_*` keeps raising.
- A crop that fails to re-embed keeps its old vector and stays selected as stale.

### 9. Concurrency

Not fixed in v1, documented. The Python API shares one session with GUI requests when the GUI runs
in the same process (`start_gui_background`). A GUI commit or delete during a long run can fail a
chunk. `add_*` has the same risk today. A real fix needs a short-lived session per chunk.

### 10. Plot

No change. A re-embedded vector has a new first float, so today's 2D cache key
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

## Testing

Resolver, one test per branch, box values in the test body (style of
tests/resolvers/annotations/test_get_unembedded_annotation_ids.py):

- missing → selected
- fingerprint matches → not selected
- box edited → selected with `include_stale`, not selected without
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
- `add_*` after a box edit does not re-embed the edited crop.

## PR split

1. Image fill fix: resolve the model first, `LEFT JOIN` in both missing queries, chunked fetch.
   No schema change.
2. Store the crop fingerprint: column, Postgres revision, BREAKING CHANGELOG entry, fingerprint
   selected with the crop and written with the vector, race test.
3. Missing-or-stale selection, upsert helper, tests on both backends, Postgres 10M measurement.
4. `compute_embeddings` on ImageDataset, in embed/embed_dataset.py, error handling, docs, CHANGELOG.
