# Embedding Recompute Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `ImageDataset.compute_embeddings`, which embeds every image and annotation crop that has no embedding of the default model, or a stale one.

**Architecture:** A new module, `embed/embed_dataset.py`, owns the image fill and the crop fill. Each fill selects first and resolves the embedder only when the selection is not empty. The `add_*` methods and `compute_embeddings` call the same fills with different flags. Crop rows store a `source_fingerprint` of the box they were cropped from. A box edit makes the stored and the current fingerprint differ, and the selection picks that row up.

**Tech Stack:** Python 3, SQLModel and SQLAlchemy, DuckDB and PostgreSQL, Alembic, pytest.

**Spec:** `.experimental/superpowers/specs/2026-10-23-embedding-recompute-design.md`

## Global Constraints

- Four PRs, in order. Each task names its PR. Branch each PR from the one before it.
- Public names, exactly: `compute_embeddings(self, embed_annotations: bool = True, recompute_annotations: bool = False) -> None`.
- Internals take `embedding_model_id`. The public API takes no model argument in v1.
- Fingerprint format: `'bbox1:' || CAST(x AS VARCHAR) || ',' || CAST(y AS VARCHAR) || ',' || CAST(width AS VARCHAR) || ',' || CAST(height AS VARCHAR)`. Raw, unclamped box. The model is not part of it.
- `add_*` selects missing rows only. It never selects stale rows, and it keeps raising `AllInputFilesFailedError`.
- `compute_embeddings` never recomputes the 2D projection.
- Image rows store `source_fingerprint = None`.
- No DuckDB migration. A schema change gets a Postgres Alembic revision and a `BREAKING:` CHANGELOG entry that tells DuckDB users to re-index.
- The Postgres revision sets `lock_timeout` before `ADD COLUMN`. Use `SET LOCAL lock_timeout = '5s'` (the spec gives no value; 5 s is this plan's choice).
- Files stay under 400 lines. `embed_samples.py` (505 lines now) must not grow.
- User-facing text (docstrings of public API, log lines, errors, docs, CHANGELOG) says "annotation source", never "annotation collection" (glossary skill).
- CHANGELOG entries follow the changelog skill: `Python SDK:` prefix, one change per entry, no internals.
- Load the path skills before editing: python-guide for all `.py`, backend-guide for `src/lightly_studio/**`, changelog for `CHANGELOG.md`.
- Run all commands from `lightly_studio/`. File paths are relative to it, except `CHANGELOG.md`, which is at the repo root. Backend tests on Postgres: add `--postgres` (testcontainers, needs Docker only).
- Stage files by name, never `git add -A`. Commit subjects use `type: description`, at most 72 characters, no body.
- Fresh worktree: run `make mock-webapp-dist` once, or conftest import fails.

## Review Focus

1. **A second `compute_embeddings` run right after the first.** Expect no new rows, unchanged vectors, and no embedder load. Test in Task 5.
2. **A box that lies fully outside its image.** The crop is skipped and never stored, so every run selects it again. Expect the run to finish, embed the rest and log the skip. Test in Task 4.
3. **An empty dataset, or one with only classification annotations, and no embedder registered.** Expect no error and no default model registered. `NoUsableEmbedderError` is for a run that has work to do. Test in Task 5.
4. **The same crop re-embedded twice in one session on DuckDB.** DuckDB upserts on indexed tables have bitten before. Expect the last vector to win. Checked by hand on DuckDB during planning; pinned in Task 3.
5. **Every chunk fails under `compute_embeddings`.** Expect the call to return, with one warning per skipped chunk that names the count. A silent success hides a moved folder. Test in Task 5.

---

## PR 1: Image fill fix

### Task 1: `LEFT JOIN` in both missing queries, `None` model selects all

**Files:**
- Modify: `src/lightly_studio/resolvers/image_resolver/get_unembedded_sample_ids.py`
- Modify: `src/lightly_studio/resolvers/annotation_resolver/get_unembedded_annotation_ids.py`
- Test: `tests/resolvers/image_resolver/test_get_unembedded_sample_ids.py`
- Test: `tests/resolvers/annotations/test_get_unembedded_annotation_ids.py`

**Interfaces:**
- Produces:

```python
def get_unembedded_sample_ids(
    session: Session, collection_id: UUID, embedding_model_id: UUID | None
) -> list[UUID]: ...

def get_unembedded_annotation_ids(
    session: Session, annotation_collection_id: UUID, embedding_model_id: UUID | None
) -> list[UUID]: ...
```

`None` means the collection has no default model yet. Then no join runs and every row (every image, every croppable annotation) is selected. Order stays `ImageTable.file_path_abs`.

- [ ] **Step 1: Write the failing tests**

```python
def test_get_unembedded_sample_ids__none_model_returns_all_images(db_session) -> None:
    # two images, one with an embedding of some model
    assert image_resolver.get_unembedded_sample_ids(
        session=db_session, collection_id=collection.collection_id, embedding_model_id=None
    ) == [image_a.sample_id, image_b.sample_id]  # path order

def test_get_unembedded_annotation_ids__none_model_returns_all_croppable(db_session) -> None:
    # one object detection, one classification, one embedded object detection
    assert ids == [detection.sample_id, embedded_detection.sample_id]  # path order, no classification
```

- [ ] **Step 2: Run them, expect FAIL**

Run: `uv run pytest tests/resolvers/image_resolver/test_get_unembedded_sample_ids.py tests/resolvers/annotations/test_get_unembedded_annotation_ids.py -v`
Expected: the two new tests fail (`None` compares against the subquery and selects nothing).

- [ ] **Step 3: Rewrite both queries**

Replace `notin_(subquery)` with an outer join on `SampleEmbeddingTable` (`sample_id` equal and `embedding_model_id == embedding_model_id`) plus `where(col(SampleEmbeddingTable.sample_id).is_(None))`. When `embedding_model_id is None`, skip the join and the filter. Update both docstrings.

- [ ] **Step 4: Run both test files on both backends, expect PASS**

Run: `uv run pytest tests/resolvers/image_resolver/test_get_unembedded_sample_ids.py tests/resolvers/annotations/test_get_unembedded_annotation_ids.py -v` and the same with `--postgres`.

- [ ] **Step 5: Commit**

```bash
git add <every file this task created or modified>
git commit -m "perf: select unembedded rows with a LEFT JOIN"
```

### Task 2: `embed_missing_images` with per-chunk fetch

**Files:**
- Create: `src/lightly_studio/embed/embed_dataset.py`
- Modify: `src/lightly_studio/embed/embed_samples.py` (delete `embed_image_samples` and `_embed_image_chunk`)
- Modify: `src/lightly_studio/core/image/image_dataset.py` (`_generate_embeddings_image`, lines 853-882)
- Create: `tests/embed/test_embed_dataset.py`
- Modify: `tests/embed/test_embed_samples.py` (move the `test_embed_image_samples*` tests out)
- Test: `tests/core/image/test_image_dataset__path.py`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: `image_resolver.get_unembedded_sample_ids` from Task 1.
- Produces:

```python
# embed/embed_dataset.py
_IMAGE_EMBED_BATCH_SIZE = 1024  # moved from embed_samples.py

def embed_missing_images(session: Session, collection_id: UUID) -> int | None:
    """Embeds every image of the collection without an embedding of the default model.

    Returns the number of stored embeddings, or None if the selection is not empty
    and no image embedder is available.
    """

def _embed_image_chunk(
    session: Session, embedder: ImagePathEmbedder, model_id: UUID, sample_ids: list[UUID]
) -> int:
    """Fetches the paths of one chunk, embeds, stores and commits it. Returns the stored count."""
```

Algorithm of `embed_missing_images`, which the signature does not fix:

```python
default_model_id = collection_embedding_model_resolver.get_default_by_collection_id(...)
sample_ids = image_resolver.get_unembedded_sample_ids(..., embedding_model_id=default_model_id)
if not sample_ids:
    return 0                      # no embedder load, no default registered
resolved = default_embedder.resolve_default_embedder(..., embedder_type=ImagePathEmbedder)
if resolved is None:
    return None
# loop over batching.batched(sample_ids, _IMAGE_EMBED_BATCH_SIZE) with the tqdm bar
```

`_embed_image_chunk` reads paths with `image_resolver.get_many_by_id` for its chunk only and raises `ValueError` when a path is missing, as `embed_image_samples` did.

- [ ] **Step 1: Move the image tests and write the new ones**

Move the `test_embed_image_samples*` tests from `test_embed_samples.py` to `test_embed_dataset.py`, renamed to `test_embed_missing_images*` and calling the new function. Drop `test_embed_image_samples__missing_id_bootstraps_no_default` and `__empty_ids_warns_and_skips`; the inputs no longer exist. Add:

```python
def test_embed_missing_images__no_default_embeds_all_and_registers(db_session) -> None:
    # 3 images, no default model
    assert embed_dataset.embed_missing_images(session=db_session, collection_id=cid) == 3
    assert collection_embedding_model_resolver.get_default_by_collection_id(...) is not None

def test_embed_missing_images__no_images_registers_no_default(db_session) -> None:
    assert embed_dataset.embed_missing_images(...) == 0
    assert collection_embedding_model_resolver.get_default_by_collection_id(...) is None

def test_embed_missing_images__nothing_missing_does_not_resolve(db_session, mocker) -> None:
    spy = mocker.spy(default_embedder, "resolve_default_embedder")
    # all images embedded already
    assert embed_dataset.embed_missing_images(...) == 0
    spy.assert_not_called()

def test_embed_missing_images__fetches_paths_per_chunk(db_session, mocker) -> None:
    mocker.patch.object(embed_dataset, "_IMAGE_EMBED_BATCH_SIZE", 2)
    spy = mocker.spy(image_resolver, "get_many_by_id")
    # 5 images
    assert embed_dataset.embed_missing_images(...) == 5
    assert [len(c.kwargs["sample_ids"]) for c in spy.call_args_list] == [2, 2, 1]
```

In `test_image_dataset__path.py`:

```python
def test_dataset_add_images_from_path__embeds_earlier_unembedded_images(...) -> None:
    dataset.add_images_from_path(path=folder_a, embed=False)
    dataset.add_images_from_path(path=folder_b, embed=True)
    # every image of folder_a and folder_b has one embedding
```

- [ ] **Step 2: Run them, expect FAIL**

Run: `uv run pytest tests/embed/test_embed_dataset.py tests/core/image/test_image_dataset__path.py -k "embed_missing_images or earlier_unembedded" -v`
Expected: `ModuleNotFoundError: lightly_studio.embed.embed_dataset`, and the dataset test finds folder_a unembedded.

- [ ] **Step 3: Implement `embed_missing_images` and `_embed_image_chunk`**

Then make `_generate_embeddings_image(session, collection_id)` call `embed_dataset.embed_missing_images`. Drop its `sample_ids` parameter and update its callers in `image_dataset.py`. Delete `embed_samples.embed_image_samples` and `embed_samples._embed_image_chunk`.

- [ ] **Step 4: Run, expect PASS**

Run: `uv run pytest tests/embed tests/core/image -v`, then `make static-checks`.

- [ ] **Step 5: CHANGELOG `Changed`**

```markdown
- Python SDK: Adding images with `embed=True` also embeds the images of the dataset that were added earlier with `embed=False`.
```

- [ ] **Step 6: Commit**

```bash
git add <every file this task created or modified>
git commit -m "fix: embed earlier unembedded images when embedding is on"
```

---

## PR 2: `compute_embeddings`

### Task 3: Upsert helper and `replace_embeddings`

**Files:**
- Modify: `src/lightly_studio/database/db_insert.py`
- Modify: `src/lightly_studio/resolvers/sample_embedding_resolver.py`
- Modify: `src/lightly_studio/embed/embedding_storage.py`
- Test: `tests/database/test_db_insert.py`
- Test: `tests/embed/test_embedding_storage.py`

**Interfaces:**
- Produces:

```python
# db_insert.py
def upsert_rows(
    session: Session,
    table: type[SQLModel],
    rows: Sequence[Mapping[str, Any]],
    conflict_columns: Sequence[str],
    update_columns: Sequence[str],
) -> None:
    """Inserts rows, and on a key conflict overwrites update_columns. Does not commit."""

# sample_embedding_resolver.py
def upsert_many(
    session: Session, sample_embeddings: list[SampleEmbeddingCreate], commit: bool = True
) -> None: ...

# embedding_storage.py
def replace_embeddings(
    session: Session,
    model_id: UUID,
    sample_ids: list[UUID],
    embeddings: NDArray[np.float32],
    show_progress: bool = True,
) -> None:
    """Like store_embeddings, but overwrites an existing embedding of the same sample and model."""
```

`upsert_rows` uses `sqlalchemy.dialects.postgresql.insert(...).on_conflict_do_update(index_elements=conflict_columns, set_={c: stmt.excluded[c] for c in update_columns})` on both backends. The repo supports only DuckDB and Postgres, and this statement runs on DuckDB (checked during planning). Batch with `batching.batched`, as `insert_ignoring_conflicts` does. `upsert_many` passes `conflict_columns=["sample_id", "embedding_model_id"]` and `update_columns=["embedding"]`. `replace_embeddings` shares `_validate_and_coerce_embeddings` and the batching loop with `store_embeddings`; extract a private helper that takes the resolver write function.

- [ ] **Step 1: Write the failing tests**

```python
def test_upsert_many__overwrites_existing_embedding(db_session) -> None:
    # create_sample_embedding(..., embedding=[0.1, 0.2, 0.3])
    sample_embedding_resolver.upsert_many(session=db_session, sample_embeddings=[<same key, [0.4, 0.5, 0.6]>])
    assert stored == [0.4, 0.5, 0.6]

def test_upsert_many__inserts_new_embedding(db_session) -> None: ...

def test_upsert_many__same_key_twice_in_one_transaction(db_session) -> None:
    # upsert_many(..., commit=False) with [0.4,...], then with [0.7,...], then commit
    assert stored == [0.7, 0.8, 0.9]

def test_create_many__keeps_first_writer(db_session) -> None:
    assert stored == [0.1, 0.2, 0.3]

def test_replace_embeddings__overwrites_and_validates(db_session) -> None:
    # overwrite works; a dimension mismatch raises ValueError like store_embeddings
```

- [ ] **Step 2: Run them, expect FAIL**

Run: `uv run pytest tests/database/test_db_insert.py tests/embed/test_embedding_storage.py -v`
Expected: `AttributeError: ... has no attribute 'upsert_many'`.

- [ ] **Step 3: Implement `upsert_rows`, `upsert_many`, `replace_embeddings`**

- [ ] **Step 4: Run on both backends, expect PASS**

Run: the same command, then with `--postgres`.

- [ ] **Step 5: Commit**

```bash
git add <every file this task created or modified>
git commit -m "feat: add an embedding upsert for re-embedding"
```

### Task 4: `embed_annotation_crops`

**Files:**
- Create: `src/lightly_studio/resolvers/annotation_resolver/get_croppable_annotation_ids.py`
- Modify: `src/lightly_studio/resolvers/annotation_resolver/__init__.py`
- Modify: `src/lightly_studio/resolvers/annotation_resolver/get_unembedded_annotation_ids.py` (build on the shared query)
- Modify: `src/lightly_studio/embed/embed_dataset.py`
- Modify: `src/lightly_studio/embed/embed_samples.py` (delete `embed_annotation_collection`, `_embed_annotation_chunk`, `_ANNOTATION_EMBED_BATCH_SIZE`)
- Modify: `src/lightly_studio/core/image/image_dataset.py` (`_generate_embeddings_annotations`)
- Test: `tests/resolvers/annotations/test_get_croppable_annotation_ids.py`
- Test: `tests/embed/test_embed_dataset.py` (move the `test_embed_annotation_collection*` tests here)

**Interfaces:**
- Consumes: `get_unembedded_annotation_ids` (Task 1), `embedding_storage.replace_embeddings` (Task 3).
- Produces:

```python
# get_croppable_annotation_ids.py
def build_croppable_annotations_query(annotation_collection_id: UUID) -> Select[tuple[UUID]]:
    """Annotation sample IDs of croppable types in the collection, joined to their image,
    ordered by image path."""

def get_croppable_annotation_ids(session: Session, annotation_collection_id: UUID) -> list[UUID]: ...

# embed_dataset.py
_ANNOTATION_EMBED_BATCH_SIZE = 2048  # moved from embed_samples.py

def embed_annotation_crops(
    session: Session,
    annotation_collection_id: UUID,
    recompute: bool = False,
    skip_failed_chunks: bool = False,
) -> int | None:
    """Embeds missing crops, or every crop with recompute. Returns the stored count,
    or None if the selection is not empty and no crop embedder is available."""

def embed_missing_images(
    session: Session, collection_id: UUID, skip_failed_chunks: bool = False
) -> int | None: ...  # Task 2's function gains the flag
```

`embed_annotation_crops` follows Task 2's order: read the default model ID, select (`get_croppable_annotation_ids` with `recompute`, else `get_unembedded_annotation_ids`), return 0 on an empty selection, then resolve with `ImageCropPathEmbedder`. The empty-selection return is spec item 7.4: a classification-only collection never resolves and never gets a default model. Crops are always written with `replace_embeddings`. With `skip_failed_chunks`, both fills catch `AllInputFilesFailedError` per chunk, log a warning with the chunk size, and continue. Without it, the error propagates.

- [ ] **Step 1: Move the annotation tests and write the new ones**

```python
def test_get_croppable_annotation_ids__skips_classification_and_orders_by_path(db_session) -> None: ...

def test_embed_annotation_crops__classification_only_registers_no_default(db_session, mocker) -> None:
    spy = mocker.spy(default_embedder, "resolve_default_embedder")
    assert embed_dataset.embed_annotation_crops(...) == 0
    spy.assert_not_called()
    assert collection_embedding_model_resolver.get_default_by_collection_id(...) is None

def test_embed_annotation_crops__recompute_overwrites_existing(db_session, mocker) -> None:
    # _BoxXImageCropEmbedder-style embedder (vector = [x, x, x], keeps all crops)
    # crop already stored as [0, 0, 0]
    embed_dataset.embed_annotation_crops(..., recompute=True)
    assert stored == {annotation_id: [box_x] * 3}

def test_embed_annotation_crops__default_keeps_existing(db_session, mocker) -> None:
    assert stored == {annotation_id: [0.0] * 3}

def test_embed_annotation_crops__dropped_crop_keeps_old_vector(db_session, mocker) -> None:
    # recompute=True, embedder drops the last crop: that crop keeps [0, 0, 0]

def test_embed_annotation_crops__box_outside_image_is_skipped(db_session, mocker, caplog) -> None:
    # one box fully outside the image, one inside
    assert embed_dataset.embed_annotation_crops(...) == 1
    assert "Skipping invalid annotation crop" in caplog.text
    assert embed_dataset.embed_annotation_crops(...) == 0  # rerun finishes too

def test_embed_annotation_crops__skip_failed_chunks_continues(db_session, mocker) -> None:
    # batch size 1, embedder raises AllInputFilesFailedError for the first chunk's path
    assert embed_dataset.embed_annotation_crops(..., skip_failed_chunks=True) == 1

def test_embed_annotation_crops__failed_chunk_raises_by_default(db_session, mocker) -> None:
    with pytest.raises(AllInputFilesFailedError): ...

def test_embed_missing_images__skip_failed_chunks_continues(db_session, mocker) -> None: ...
```

Copy `_BoxXImageCropEmbedder` into `test_embed_dataset.py` with a `drop_last: bool` constructor flag; the copy in `test_embed_samples.py` goes away with the moved tests.

- [ ] **Step 2: Run them, expect FAIL**

Run: `uv run pytest tests/embed/test_embed_dataset.py tests/resolvers/annotations -v`

- [ ] **Step 3: Implement**

Add the resolver and export both functions from `annotation_resolver/__init__.py`. Rebuild `get_unembedded_annotation_ids` on `build_croppable_annotations_query`. Add `embed_annotation_crops`, move `_embed_annotation_chunk` into `embed_dataset.py` and make it return the stored count, not the resolved count. Point `_generate_embeddings_annotations` at `embed_dataset.embed_annotation_crops`. Delete the old functions from `embed_samples.py`.

- [ ] **Step 4: Run, expect PASS**

Run: `uv run pytest tests/embed tests/resolvers/annotations tests/core/image -v`, then `make static-checks`. Check `wc -l src/lightly_studio/embed/embed_samples.py src/lightly_studio/embed/embed_dataset.py`: both under 400.

- [ ] **Step 5: Commit**

```bash
git add <every file this task created or modified>
git commit -m "refactor: move crop embedding to embed_dataset"
```

### Task 5: `compute_embeddings`, error, docs, CHANGELOG

**Files:**
- Modify: `src/lightly_studio/embed/errors.py`
- Modify: `src/lightly_studio/embed/embed_dataset.py`
- Modify: `src/lightly_studio/core/image/image_dataset.py`
- Create: `tests/core/image/test_image_dataset__compute_embeddings.py`
- Modify: `docs/docs/workflows/embeddings.md:52-54`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: `embed_missing_images`, `embed_annotation_crops` (Task 4), `collection_resolver.get_annotation_collections(session, parent_collection_id)`.
- Produces:

```python
# errors.py
class NoUsableEmbedderError(Exception):
    """Raised when samples need an embedding and no embedder is available for them."""

# embed_dataset.py
def compute_embeddings(
    session: Session,
    collection_id: UUID,
    embed_annotations: bool,
    recompute_annotations: bool,
) -> None: ...

# image_dataset.py, on ImageDataset
def compute_embeddings(
    self, embed_annotations: bool = True, recompute_annotations: bool = False
) -> None:
    """Embeds images and annotation crops that have no embedding or a stale one."""
```

`embed_dataset.compute_embeddings` runs `embed_missing_images` first (spec 7.3), then `embed_annotation_crops` for each annotation collection of `get_annotation_collections`, all with `skip_failed_chunks=True`. A `None` from any fill raises `NoUsableEmbedderError`. At the end it logs one info line with the image count and the annotation count. The `ImageDataset` method passes `self.session` and `self.collection_id`. Its docstring covers both flags, and says that until stale detection lands, edited boxes need `recompute_annotations=True` (PR 4 removes that sentence).

- [ ] **Step 1: Write the failing tests**

All in `test_image_dataset__compute_embeddings.py`, using real image files in `tmp_path` and the conftest `RandomEmbedder`. `RandomEmbedder` never opens a file, so the two failed-chunk tests patch the registry with a test-only `_MissingFileImageEmbedder(ImagePathEmbedder)` that raises `AllInputFilesFailedError` when no path of its input exists, and returns zeros otherwise. Declare its space as `random_model`, dimension 3, like `_PathOnlyEmbedder` in `tests/embed/test_embed_samples.py`.

```python
def test_compute_embeddings__dataset_added_without_embedding(...) -> None:
    dataset.add_images_from_path(path=tmp_path, embed=False)
    # add one detection per image, embed_annotations=False
    dataset.compute_embeddings()
    # every image and every detection has one embedding of the default model

def test_compute_embeddings__every_annotation_source(...) -> None:
    # two annotation sources, e.g. "ground_truth" and "predictions": both get embeddings

def test_compute_embeddings__embed_annotations_false(...) -> None:
    # images embedded, annotations not

def test_compute_embeddings__recompute_annotations(...) -> None:
    # crop stored with a known vector; default call keeps it, recompute_annotations=True replaces it

def test_compute_embeddings__second_run_is_noop(..., mocker) -> None:   # Review Focus 1
    dataset.compute_embeddings()
    before = <all stored vectors>
    spy = mocker.spy(default_embedder, "resolve_default_embedder")
    dataset.compute_embeddings()
    assert <all stored vectors> == before
    spy.assert_not_called()

def test_compute_embeddings__no_usable_embedder_raises(..., mocker) -> None:
    # registry patched to an empty EmbedderRegistry, one unembedded image
    with pytest.raises(NoUsableEmbedderError):
        dataset.compute_embeddings()

def test_compute_embeddings__nothing_to_embed_and_no_embedder(..., mocker) -> None:  # Review Focus 3
    # empty dataset, plus one with only classification annotations; empty registry
    dataset.compute_embeddings()  # does not raise
    assert collection_embedding_model_resolver.get_default_by_collection_id(...) is None

def test_compute_embeddings__failed_chunk_is_logged_and_next_embedded(..., mocker, caplog) -> None:
    # _IMAGE_EMBED_BATCH_SIZE = 1, first image file deleted after adding,
    # registry patched with _MissingFileImageEmbedder
    dataset.compute_embeddings()
    # second image embedded, warning names the skipped chunk

def test_compute_embeddings__every_chunk_fails(..., mocker, caplog) -> None:  # Review Focus 5
    # all image files deleted, batch size 1, 3 images, _MissingFileImageEmbedder
    dataset.compute_embeddings()  # returns
    assert caplog.text.count(<skip warning text>) == 3
```

- [ ] **Step 2: Run them, expect FAIL**

Run: `uv run pytest tests/core/image/test_image_dataset__compute_embeddings.py -v`
Expected: `AttributeError: 'ImageDataset' object has no attribute 'compute_embeddings'`.

- [ ] **Step 3: Implement the error, the orchestration and the method**

- [ ] **Step 4: Run, expect PASS**

Run: `uv run pytest tests/core/image tests/embed -v`, then `make static-checks`.

- [ ] **Step 5: Docs**

In `docs/docs/workflows/embeddings.md`, replace the warning at lines 52-54 with a section on `compute_embeddings`: a short example, what each flag does, and that edited boxes need `recompute_annotations=True`. Add, as notes:

- Re-embedding does not refresh typicality metadata, similarity metadata, or an active lasso region on the embedding plot. Recompute those after.
- Do not edit annotations in the GUI while `compute_embeddings` runs.
- On DuckDB, each re-embedded row is rewritten, about 3.3 KB per 512-dimension embedding, and `CHECKPOINT` does not reclaim the space.

Write it with the simple-english skill. Use "annotation source".

- [ ] **Step 6: CHANGELOG `Added`**

```markdown
- Python SDK: `ImageDataset.compute_embeddings()` embeds the images and annotations that have no embedding, for example after adding them with `embed=False` or creating annotations in the GUI. Pass `recompute_annotations=True` to re-embed every annotation.
```

- [ ] **Step 7: Commit**

```bash
git add <every file this task created or modified>
git commit -m "feat: add ImageDataset.compute_embeddings"
```

---

## PR 3: `BREAKING:` Store the crop fingerprint with annotation embeddings

### Task 6: `source_fingerprint` column and Postgres revision

**Files:**
- Modify: `src/lightly_studio/models/sample_embedding.py`
- Create: `src/lightly_studio/migrations/versions/<generated>_add_sample_embedding_source_fingerprint.py`
- Test: `tests/database/test_db_migrations.py`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Produces: `SampleEmbeddingBase.source_fingerprint: str | None = None`, so `SampleEmbeddingCreate` and `SampleEmbeddingTable` both carry it.

- [ ] **Step 1: Write the failing migration test**

Model it on `test_postgres_embedding_model_api_key__added_and_dropped` (line 424): upgrade to the revision before this one, insert a dataset, an embedding model, a sample and a `sample_embedding` row, upgrade to head, then assert:

```python
assert source_fingerprint_column["nullable"] is True
assert connection.execute(text("SELECT source_fingerprint FROM sample_embedding")).scalar_one() is None
command.check(config)  # model and revision agree
# downgrade one step: column gone, row kept
```

- [ ] **Step 2: Run, expect FAIL**

Run: `uv run pytest tests/database/test_db_migrations.py -k source_fingerprint --postgres -v`

- [ ] **Step 3: Add the field and generate the revision**

Run `uv run alembic -c alembic.ini heads` and `uv run alembic -c alembic.ini revision -m "add_sample_embedding_source_fingerprint"`. Check that `down_revision` is the head. `upgrade()`:

```python
op.execute("SET LOCAL lock_timeout = '5s'")
op.add_column("sample_embedding", sa.Column("source_fingerprint", sa.String(), nullable=True))
```

`downgrade()` drops the column.

- [ ] **Step 4: Run, expect PASS**

Run: `uv run pytest tests/database --postgres -v`, then `uv run pytest tests/database -v` for DuckDB.

- [ ] **Step 5: CHANGELOG under `Changed`**

```markdown
- BREAKING: Annotation embeddings now remember the box they were computed from. The PostgreSQL migration is automatic. DuckDB users must re-index their data.
```

- [ ] **Step 6: Commit**

```bash
git add <every file this task created or modified>
git commit -m "feat: add source_fingerprint to sample_embedding"
```

### Task 7: Select and write the fingerprint with the crop

**Files:**
- Modify: `src/lightly_studio/resolvers/annotation_resolver/get_annotation_crops.py`
- Modify: `src/lightly_studio/embed/embedding_storage.py`
- Modify: `src/lightly_studio/embed/embed_dataset.py` (`_embed_annotation_chunk`)
- Modify: `src/lightly_studio/resolvers/sample_embedding_resolver.py` (`upsert_many` updates `source_fingerprint`)
- Test: `tests/resolvers/annotations/test_get_annotation_crops.py` (create if missing)
- Test: `tests/embed/test_embed_dataset.py`

**Interfaces:**
- Consumes: `SampleEmbeddingCreate.source_fingerprint` (Task 6), `replace_embeddings` (Task 3).
- Produces:

```python
# get_annotation_crops.py
CROP_FINGERPRINT_PREFIX = "bbox1:"

def build_crop_fingerprint_expression() -> ColumnElement[str]:
    """The crop fingerprint of an annotation's raw box, as SQL.

    The query must outer join ObjectDetectionAnnotationTable and SegmentationAnnotationTable
    on the annotation's sample_id.
    """

@dataclass(frozen=True)
class AnnotationCrop:
    annotation_sample_id: UUID
    image_crop: ImageCrop
    source_fingerprint: str

# embedding_storage.py
def replace_embeddings(
    session: Session,
    model_id: UUID,
    sample_ids: list[UUID],
    embeddings: NDArray[np.float32],
    source_fingerprints: list[str],
    show_progress: bool = True,
) -> None: ...
```

The expression concatenates `CROP_FINGERPRINT_PREFIX` with `cast(func.coalesce(od.x, seg.x), String)`, a comma, and the same for `y`, `width` and `height`. The crop query adds it as a fifth selected column, so the box and the fingerprint come from one read. `upsert_many` adds `source_fingerprint` to `update_columns`. `replace_embeddings` raises `ValueError` when `len(source_fingerprints) != len(sample_ids)`. `_embed_annotation_chunk` passes the fingerprints of the kept crops.

- [ ] **Step 1: Write the failing tests**

```python
def test_get_annotation_crops_for_ids__fingerprint_matches_raw_box(db_session) -> None:
    # detection with x=-5, y=3, width=20, height=10 on a 100x100 image
    assert crop.source_fingerprint == "bbox1:-5,3,20,10"
    assert crop.image_crop.x == 0  # clamped; the fingerprint is not

def test_get_annotation_crops_for_ids__segmentation_fingerprint(db_session) -> None: ...

def test_embed_annotation_crops__stores_fingerprint(db_session, mocker) -> None:
    # stored row's source_fingerprint equals get_annotation_crops_for_ids(...)[0].source_fingerprint

def test_embed_annotation_crops__box_edited_during_run(db_session, mocker) -> None:
    # Spec "Race". The embedder's embed_image_crops calls
    # annotation_resolver.update_bounding_box(session, annotation_id, BoundingBoxCoordinates(x=30, ...))
    # before returning [x, x, x] for the crop it was given (old x=10).
    embed_dataset.embed_annotation_crops(...)
    assert stored_vector == [10.0] * 3
    current = annotation_resolver.get_annotation_crops_for_ids(...)[0].source_fingerprint
    assert stored_fingerprint != current
```

The first test pins the format on purpose: it is the one place the literal lives in tests.

- [ ] **Step 2: Run, expect FAIL**

Run: `uv run pytest tests/resolvers/annotations/test_get_annotation_crops.py tests/embed/test_embed_dataset.py -v`

- [ ] **Step 3: Implement**

- [ ] **Step 4: Run on both backends, expect PASS**

Run: the same command, then with `--postgres`. Then `make static-checks`.

- [ ] **Step 5: Commit**

```bash
git add <every file this task created or modified>
git commit -m "feat: store the crop fingerprint with annotation embeddings"
```

---

## PR 4: Missing-or-stale selection

### Task 8: Stale selection and the default `compute_embeddings`

**Files:**
- Modify: `src/lightly_studio/resolvers/annotation_resolver/get_unembedded_annotation_ids.py`
- Modify: `src/lightly_studio/embed/embed_dataset.py`
- Modify: `src/lightly_studio/core/image/image_dataset.py` (docstring)
- Test: `tests/resolvers/annotations/test_get_unembedded_annotation_ids.py`
- Test: `tests/core/image/test_image_dataset__compute_embeddings.py`
- Modify: `docs/docs/workflows/embeddings.md`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: `build_crop_fingerprint_expression` (Task 7), `build_croppable_annotations_query` (Task 4).
- Produces:

```python
def get_unembedded_annotation_ids(
    session: Session,
    annotation_collection_id: UUID,
    embedding_model_id: UUID | None,
    include_stale: bool = False,
) -> list[UUID]: ...

def _is_stale_clause() -> ColumnElement[bool]:
    """SampleEmbeddingTable.source_fingerprint differs from the current crop fingerprint.
    A NULL fingerprint is not stale."""

def embed_annotation_crops(
    session: Session,
    annotation_collection_id: UUID,
    recompute: bool = False,
    include_stale: bool = False,
    skip_failed_chunks: bool = False,
) -> int | None: ...
```

With `include_stale`, the query outer joins both detail tables and filters on `missing OR _is_stale_clause()`. Use SQL `<>` (`!=` in SQLAlchemy) so `NULL` stays not stale. `compute_embeddings` passes `include_stale=True`; `add_*` passes nothing.

- [ ] **Step 1: Write the failing resolver tests**

One test per branch, box values in the test body, in the style of the existing file:

```python
def test_get_unembedded_annotation_ids__missing_is_selected(db_session) -> None: ...
def test_get_unembedded_annotation_ids__matching_fingerprint_not_selected(db_session) -> None:
    # embedding row with source_fingerprint="bbox1:50,50,20,20" (the helper's default box)
def test_get_unembedded_annotation_ids__edited_box_selected_only_with_include_stale(db_session) -> None:
    # row stored with "bbox1:50,50,20,20", then update_bounding_box to x=60
    assert ids(include_stale=True) == [annotation.sample_id]
    assert ids(include_stale=False) == []
def test_get_unembedded_annotation_ids__null_fingerprint_not_selected(db_session) -> None: ...
```

`create_sample_embedding` in `tests/helpers_resolvers.py` gets a `source_fingerprint: str | None = None` parameter.

- [ ] **Step 2: Write the failing round-trip and API tests**

```python
def test_embed_annotation_crops__round_trip_negative_x(db_session, mocker) -> None:
    # Spec "Round trip": detection with x=-5 (clamped crop differs from raw box)
    embed_dataset.embed_annotation_crops(...)
    assert get_unembedded_annotation_ids(..., include_stale=True) == []
    annotation_resolver.update_bounding_box(..., BoundingBoxCoordinates(x=-4, y=..., ...))
    assert get_unembedded_annotation_ids(..., include_stale=True) == [annotation_id]
```

No format literal in this test. It locks the writer and the SQL expression together. In `test_image_dataset__compute_embeddings.py`:

```python
def test_compute_embeddings__edited_box_gets_new_vector(...) -> None:
    # two detections; edit one box; compute_embeddings()
    # edited one has a new vector, the other keeps its vector

def test_compute_embeddings__legacy_row_needs_recompute(...) -> None:
    # crop row with source_fingerprint=None: default call keeps it, recompute_annotations=True replaces it

def test_add_annotations__does_not_reembed_edited_box(...) -> None:
    # edit a box, then add_annotations_from_coco(...) with embed_annotations=True
    # edited crop keeps its old vector
```

Extend Task 7's `test_embed_annotation_crops__box_edited_during_run` with a stale-selection check, as a new test:

```python
def test_embed_annotation_crops__box_edited_during_run_is_stale_after(db_session, mocker) -> None:
    assert get_unembedded_annotation_ids(..., include_stale=True) == [annotation_id]
```

- [ ] **Step 3: Run, expect FAIL**

Run: `uv run pytest tests/resolvers/annotations/test_get_unembedded_annotation_ids.py tests/embed/test_embed_dataset.py tests/core/image/test_image_dataset__compute_embeddings.py -v`

- [ ] **Step 4: Implement the clause, the parameter and the default**

Remove the "until stale detection lands" sentence from the `compute_embeddings` docstring.

- [ ] **Step 5: Run on both backends, expect PASS**

Run: the Step 3 command, then with `--postgres`. Then `make static-checks`.

- [ ] **Step 6: Measure on Postgres with 10M annotations**

The spec's risk section says PR 3 measures this; the stale query first exists here, so PR 4 does it. Seed a scratch Postgres (not the `make start-postgres` one, it collides with port 5433) with 10M object detections and their crop embeddings, using `INSERT ... SELECT` over `generate_series`. Run `EXPLAIN (ANALYZE, BUFFERS)` on the query from `get_unembedded_annotation_ids` with `include_stale=False` and with `include_stale=True`. Record wall time and shared blocks read for both, and whether `sample_embedding.embedding` is stored in TOAST, in the PR description. Keep the seed script out of the PR. If the stale query takes more than twice the missing query's time, open a follow-up for the covering index:

```sql
CREATE INDEX ... ON sample_embedding (embedding_model_id, sample_id) INCLUDE (source_fingerprint);
```

- [ ] **Step 7: Docs and CHANGELOG**

In `embeddings.md`, replace "edited boxes need `recompute_annotations=True`" with: the default call re-embeds annotations whose box changed, and `recompute_annotations=True` is for embeddings from before this version or after changing a custom embedder. CHANGELOG `Changed`:

```markdown
- Python SDK: `compute_embeddings()` re-embeds annotations whose box was moved or resized.
```

- [ ] **Step 8: Commit**

```bash
git add <every file this task created or modified>
git commit -m "feat: re-embed annotations with an edited box"
```
