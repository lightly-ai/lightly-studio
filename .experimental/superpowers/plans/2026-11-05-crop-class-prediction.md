# Crop Class Prediction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** After a box or brush mask is created in the image editor, predict its class from the crop and let the user switch to one of the top 3 with keys 1–3.

**Architecture:** A new route embeds the annotation's crop, stores the embedding, and scores every class with KNN over other annotation crop embeddings plus one text anchor per class. The editor creates the annotation with the last-used class as today, then calls the route and shows the top 3 in a strip.

**Tech Stack:** FastAPI, SQLModel, DuckDB/Postgres vector distance (`db_vector`), the embedder registry; SvelteKit, Svelte 5 runes, TanStack Query, generated hey-api client, vitest.

**Spec:** `.experimental/superpowers/specs/2026-11-05-crop-class-prediction-design.md`

## Global Constraints

- Load the skills from `AGENTS.md` before editing: `python-guide` and `backend-guide` for `lightly_studio/src/lightly_studio/**`, `frontend-guide` for `lightly_studio_view/**`, `glossary` for user-facing text.
- KNN neighbours: k = 10.
- Text anchor prompt: `"a photo of a {class}"`.
- Text anchor weight λ = 3.
- Route: `POST /api/collections/{collection_id}/annotations/{annotation_id}/class_predictions`.
- Response: every class of the dataset, sorted by score descending, scores sum to 1 (or all 0). No `top_n` parameter.
- Only object-detection and segmentation-mask annotations (`CROPPABLE_ANNOTATION_TYPES`).
- Strip text while loading: `Predicting class…`.
- Out of scope: video, cuboids, Smart Select, Find Instances, classification annotations, auto-apply, the popover.
- Deviation from spec naming: the service lives in `services/annotations_service/` as `predict_annotation_classes`, following that package's one-function-per-file pattern, instead of a new `annotation_class_prediction_service` package.

## Review Focus

1. A dataset class with no annotations and no text embedder must come back with score 0, not be missing. Test in Task 3.
2. A box fully outside the image (no valid crop) returns `[]`, never a 500. Test in Task 3.
3. Drawing a second box before the first prediction returns must not show or apply the first box's prediction. Test in Task 5.
4. Typing 1–3 into a text input (class dialog, search) must not relabel. Test in Task 6.
5. The annotation deleted before its prediction returns (404) hides the strip silently. Test in Task 5.

---

## Setup (once per worktree, before Task 1)

```bash
cd lightly_studio && make export-schema && make export-version && make mock-webapp-dist
cd ../lightly_studio_view && npm ci && npm run generate-api-client && npm run generate-language
```

`make export-schema` deletes the webapp dist, so `make mock-webapp-dist` must run after it.

---

### Task 1: KNN resolver

**Files:**
- Create: `lightly_studio/src/lightly_studio/resolvers/annotation_resolver/get_nearest_labeled_annotations.py`
- Modify: `lightly_studio/src/lightly_studio/resolvers/annotation_resolver/__init__.py` (export it)
- Test: `lightly_studio/tests/resolvers/annotations/test_get_nearest_labeled_annotations.py`

**Interfaces:**
- Produces:

```python
@dataclass(frozen=True)
class AnnotationNeighbour:
    annotation_label_id: UUID
    similarity: float  # 1 - cosine distance

def get_nearest_labeled_annotations(
    session: Session,
    annotation_collection_id: UUID,
    embedding_model_id: UUID,
    query_embedding: list[float],
    exclude_annotation_id: UUID,
    limit: int,
) -> list[AnnotationNeighbour]: ...
```

- [x] **Step 1: Write the failing tests**

Build fixtures like `test_get_unembedded_annotation_ids.py`: one root collection, its annotation child collection, two labels, images, annotations, `create_embedding_model` on the annotation collection, `create_sample_embedding` per annotation with 3-dim vectors.

```python
def test_get_nearest_labeled_annotations__orders_by_similarity_and_limits() -> None:
    # embeddings: a=[1,0,0] (cat), b=[0.9,0.1,0] (dog), c=[0,1,0] (cat); query=[1,0,0]
    # limit=2 → [cat (a), dog (b)], similarities descending, a's similarity == pytest.approx(1.0)

def test_get_nearest_labeled_annotations__excludes_query_annotation() -> None:
    # query annotation has an identical stored embedding; it is not in the result

def test_get_nearest_labeled_annotations__ignores_other_model_and_other_collection() -> None:
    # a second embedding model on the same annotation, and an annotation in a second
    # annotation collection, both closer to the query → neither appears
```

- [x] **Step 2: Run tests to verify they fail**

Run: `cd lightly_studio && uv run pytest tests/resolvers/annotations/test_get_nearest_labeled_annotations.py -v`
Expected: FAIL with `ImportError` / `AttributeError` for `get_nearest_labeled_annotations`.

- [x] **Step 3: Implement `get_nearest_labeled_annotations`**

One `select` of `AnnotationBaseTable.annotation_label_id` and `db_vector.cosine_distance(SampleEmbeddingTable.embedding, query_embedding)`, joined on `SampleTable` (filter `collection_id == annotation_collection_id`) and `SampleEmbeddingTable` (filter `embedding_model_id`), excluding `exclude_annotation_id`, ordered by distance, `limit`. Map distance with `similarity_utils.distance_to_similarity`.

- [x] **Step 4: Run tests to verify they pass**

Run: same as Step 2. Expected: 3 passed.

- [x] **Step 5: Run the Postgres variant**

Run: `cd lightly_studio && uv run pytest --postgres tests/resolvers/annotations/test_get_nearest_labeled_annotations.py -v`
Expected: 3 passed.

- [x] **Step 6: Commit**

```bash
git add lightly_studio/src/lightly_studio/resolvers/annotation_resolver/ lightly_studio/tests/resolvers/annotations/test_get_nearest_labeled_annotations.py
git commit -m "feat: add nearest labeled annotations resolver"
```

---

### Task 2: Class scoring (human contribution)

The scoring rule is the one free design choice in the feature. During execution, the session writes the tests and the signature, places a single `TODO(human)` in the function body, and hands the body to the user as a Learn by Doing request. The rule in the spec is the default; the user may refine it.

**Files:**
- Create: `lightly_studio/src/lightly_studio/services/annotations_service/class_prediction_scoring.py`
- Test: `lightly_studio/tests/services/annotations_service/test_class_prediction_scoring.py`

**Interfaces:**
- Consumes: `AnnotationNeighbour` from Task 1.
- Produces:

```python
TEXT_ANCHOR_WEIGHT = 3.0

def score_classes(
    label_ids: list[UUID],
    neighbours: list[AnnotationNeighbour],
    text_similarities: dict[UUID, float],
    text_anchor_weight: float = TEXT_ANCHOR_WEIGHT,
) -> dict[UUID, float]:
    """One score per id in label_ids. Sum is 1, or every score is 0 when there is no evidence."""
```

Spec rule: `score(c) = Σ similarity of c's neighbours + text_anchor_weight · text_similarity(c)`, then divide by the total. Negative raw scores clip to 0 before normalizing.

- [x] **Step 1: Write the failing tests**

```python
def test_score_classes__knn_only() -> None:
    # neighbours: cat 0.9, cat 0.8, dog 0.7; no text → cat == approx(1.7/2.4), dog == approx(0.7/2.4)

def test_score_classes__text_only() -> None:
    # no neighbours; text cat 0.3, dog 0.1 → cat == approx(0.75), dog == approx(0.25)

def test_score_classes__blends_text_and_knn() -> None:
    # neighbours: cat 0.8; text cat 0.2, dog 0.3, weight 3 → raw cat 1.4, dog 0.9

def test_score_classes__no_evidence_returns_all_zero() -> None:
    # no neighbours, no text, 2 labels → {cat: 0.0, dog: 0.0}, no ZeroDivisionError

def test_score_classes__returns_every_label() -> None:
    # 3 label_ids, neighbours only for one → 3 keys, others 0.0
```

- [x] **Step 2: Run tests to verify they fail**

Run: `cd lightly_studio && uv run pytest tests/services/annotations_service/test_class_prediction_scoring.py -v`
Expected: FAIL (`NotImplementedError` from the `TODO(human)` stub).

- [x] **Step 3: User implements `score_classes`** (Learn by Doing)

- [x] **Step 4: Run tests to verify they pass**

Run: same as Step 2. Expected: 5 passed.

- [x] **Step 5: Commit**

```bash
git add lightly_studio/src/lightly_studio/services/annotations_service/class_prediction_scoring.py lightly_studio/tests/services/annotations_service/test_class_prediction_scoring.py
git commit -m "feat: add class scoring for crop class prediction"
```

---

### Task 3: Prediction service

**Files:**
- Modify: `lightly_studio/src/lightly_studio/embed/embed_samples.py` — rename `_embed_annotation_chunk` to `embed_annotation_crops` (public), update its one caller.
- Create: `lightly_studio/src/lightly_studio/services/annotations_service/predict_annotation_classes.py`
- Modify: `lightly_studio/src/lightly_studio/services/annotations_service/__init__.py` (export)
- Test: `lightly_studio/tests/services/annotations_service/test_predict_annotation_classes.py`

**Interfaces:**
- Consumes: `get_nearest_labeled_annotations` (Task 1), `score_classes` (Task 2).
- Produces:

```python
# embed_samples.py
def embed_annotation_crops(
    session: Session,
    embedder: ImageCropPathEmbedder,
    model_id: UUID,
    annotation_sample_ids: list[UUID],
) -> int: ...

# predict_annotation_classes.py
@dataclass(frozen=True)
class AnnotationClassPrediction:
    annotation_label_id: UUID
    label_name: str
    score: float

KNN_NEIGHBOUR_COUNT = 10
TEXT_ANCHOR_PROMPT = "a photo of a {class_name}"

def predict_annotation_classes(
    session: Session,
    annotation: AnnotationBaseTable,
) -> list[AnnotationClassPrediction]: ...
```

The caller (Task 4) has already checked that the annotation exists and is croppable.

- [ ] **Step 1: Write the failing tests**

Use the `patched_registry` pattern from `tests/embed/test_embed_samples.py` (a fresh `EmbedderRegistry` with `RandomEmbedder`, patched into `embedder_registry.get_registry`). `RandomEmbedder` embeds crops and text. Images need real files for cropping: write small PNGs to `tmp_path`.

```python
def test_predict_annotation_classes__returns_every_dataset_label_sorted() -> None:
    # 3 labels, 1 annotation → 3 predictions, scores descending, sum == approx(1.0)

def test_predict_annotation_classes__stores_the_crop_embedding() -> None:
    # after the call, get_unembedded_annotation_ids(...) no longer contains the annotation

def test_predict_annotation_classes__no_crop_embedder_returns_empty(mocker) -> None:
    # empty EmbedderRegistry patched in → []

def test_predict_annotation_classes__no_text_embedder_and_no_neighbours_returns_zeros(mocker) -> None:
    # registry with a crop-only embedder (subclass exposing only embed_image_crops), single
    # annotation → every label present with score 0.0  (Review Focus 1)

def test_predict_annotation_classes__box_outside_image_returns_empty() -> None:
    # annotation x=10_000 on a 64×64 image → []  (Review Focus 2)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd lightly_studio && uv run pytest tests/services/annotations_service/test_predict_annotation_classes.py -v`
Expected: FAIL with `ImportError` for `predict_annotation_classes`.

- [ ] **Step 3: Rename `_embed_annotation_chunk` to `embed_annotation_crops`**

Run `uv run pytest tests/embed/test_embed_samples.py` after the rename. Expected: unchanged pass count.

- [ ] **Step 4: Implement `predict_annotation_classes`**

Order:
1. Annotation collection = the annotation's `SampleTable.collection_id`. `resolve_default_embedder(..., embedder_type=ImageCropPathEmbedder)`; `None` → `[]`.
2. `embed_annotation_crops(...)` for this annotation; result `0` → `[]`. Read the stored vector back with the sample embedding resolver.
3. `get_nearest_labeled_annotations(..., limit=KNN_NEIGHBOUR_COUNT)`.
4. Labels: `annotation_label_resolver.get_all(dataset_id=...)` of the collection's dataset.
5. Text: `resolve_query_embedder(..., embedder_type=TextEmbedder)`; catch `MissingCapabilityError` → no anchors. Embed only class names missing from a module-level `dict[tuple[UUID, str], NDArray[np.float32]]` cache, in one `embed_text` call. Similarity = dot product of L2-normalized vectors.
6. `score_classes(...)`, map to `AnnotationClassPrediction`, sort descending by score, then by label name for ties.

- [ ] **Step 5: Run tests to verify they pass**

Run: same as Step 2. Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add lightly_studio/src/lightly_studio/embed/embed_samples.py lightly_studio/src/lightly_studio/services/annotations_service/ lightly_studio/tests/services/annotations_service/test_predict_annotation_classes.py
git commit -m "feat: add annotation class prediction service"
```

---

### Task 4: Route

**Files:**
- Create: `lightly_studio/src/lightly_studio/api/routes/api/annotations/predict_annotation_classes.py`
- Modify: `lightly_studio/src/lightly_studio/api/routes/api/annotations/__init__.py` (export router)
- Modify: `lightly_studio/src/lightly_studio/api/routes/api/annotation.py:52-56` (`include_router`)
- Test: `lightly_studio/tests/api/routes/api/annotations/test_predict_annotation_classes.py`

**Interfaces:**
- Consumes: `predict_annotation_classes`, `AnnotationClassPrediction` (Task 3).
- Produces: `predict_annotation_classes_router`; response model `AnnotationClassPredictionView` (`annotation_label_id: UUID`, `label_name: str`, `score: float`). The generated client exposes `predictAnnotationClasses` and `predictAnnotationClassesMutation`.

- [ ] **Step 1: Write the failing tests**

```python
def test_predict_annotation_classes__ok(test_client, mocker) -> None:
    # service mocked to return 2 predictions → 200, JSON list of 2 in the same order

def test_predict_annotation_classes__annotation_not_found(test_client) -> None:
    # random UUID → 404

def test_predict_annotation_classes__not_croppable(test_client) -> None:
    # classification annotation → 400
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd lightly_studio && uv run pytest tests/api/routes/api/annotations/test_predict_annotation_classes.py -v`
Expected: FAIL with 404 on every test (route missing).

- [ ] **Step 3: Implement the route**

`annotation_resolver.get_by_id` → `HTTPException(HTTP_STATUS_NOT_FOUND)`; type not in `CROPPABLE_ANNOTATION_TYPES` → `HTTPException(HTTP_STATUS_BAD_REQUEST)`; else call the service.

- [ ] **Step 4: Run tests and static checks**

Run: `cd lightly_studio && uv run pytest tests/api/routes/api/annotations/test_predict_annotation_classes.py -v && make static-checks`
Expected: 3 passed, static checks clean.

- [ ] **Step 5: Regenerate the client**

Run: `cd lightly_studio && make export-schema && make mock-webapp-dist && cd ../lightly_studio_view && npm run generate-api-client`
Expected: `predictAnnotationClasses` appears in `src/lib/api/lightly_studio_local/sdk.gen.ts`.

- [ ] **Step 6: Commit**

```bash
git add lightly_studio/src/lightly_studio/api/routes/api/ lightly_studio/tests/api/routes/api/annotations/test_predict_annotation_classes.py
git commit -m "feat: add annotation class predictions route"
```

---

### Task 5: Prediction state hook

**Files:**
- Create: `lightly_studio_view/src/lib/hooks/useAnnotationClassPrediction/useAnnotationClassPrediction.svelte.ts`
- Test: `lightly_studio_view/src/lib/hooks/useAnnotationClassPrediction/useAnnotationClassPrediction.test.ts`

**Interfaces:**
- Consumes: generated `predictAnnotationClasses` (Task 4).
- Produces:

```ts
export type ClassPredictionState =
    | { status: 'hidden' }
    | { status: 'loading'; annotationId: string }
    | { status: 'ready'; annotationId: string; top: AnnotationClassPredictionView[] }; // top.length <= 3

export function createAnnotationClassPredictionContext(): AnnotationClassPredictionContext;
export function useAnnotationClassPredictionContext(): AnnotationClassPredictionContext;

type AnnotationClassPredictionContext = {
    readonly state: ClassPredictionState;
    predict(params: { collectionId: string; annotationId: string }): Promise<void>;
    hide(): void;
};
```

Context pattern as in `lib/contexts/SampleDetailsAnnotation.svelte.ts`.

- [ ] **Step 1: Write the failing tests** (mock `predictAnnotationClasses`)

```ts
it('goes loading → ready with the top 3 of the response');
it('hides when the response is empty');
it('hides on a request error, including 404');           // Review Focus 5
it('drops a late response for an older annotation');     // Review Focus 3:
// predict(A) pending, predict(B) resolves first, then A resolves → state stays B
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd lightly_studio_view && npx vitest run src/lib/hooks/useAnnotationClassPrediction`
Expected: FAIL, module not found.

- [ ] **Step 3: Implement the hook**

Track the latest requested annotation ID; ignore a resolution whose ID is not the latest.

- [ ] **Step 4: Run tests to verify they pass**

Run: same as Step 2. Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add lightly_studio_view/src/lib/hooks/useAnnotationClassPrediction/
git commit -m "feat: add annotation class prediction state"
```

---

### Task 6: Strip, keys and call sites

**Files:**
- Create: `lightly_studio_view/src/lib/components/SampleDetails/ClassPredictionStrip/ClassPredictionStrip.svelte`
- Test: `lightly_studio_view/src/lib/components/SampleDetails/ClassPredictionStrip/ClassPredictionStrip.test.ts`
- Modify: `lightly_studio_view/src/lib/components/SampleDetails/SampleDetailsPanel.svelte` (create context, mount strip under the toolbar)
- Modify: `lightly_studio_view/src/lib/components/SampleDetails/SampleObjectDetectionRect/SampleObjectDetectionRect.svelte` (after `createAnnotation` at ~:215, call `predict`)
- Modify: `lightly_studio_view/src/lib/hooks/useSegmentationMaskBrush.ts` (after the create branch of `finishBrush` at ~:169, call `predict`)

**Interfaces:**
- Consumes: `useAnnotationClassPredictionContext` (Task 5), `useUpdateAnnotationsMutation`, `addAnnotationLabelChangeToUndoStack`, `useAnnotationLabelContext`.
- Produces: `ClassPredictionStrip` with props `{ collectionId: string }`.

Rendering: `loading` → spinner + `Predicting class…`. `ready` → `1 car 82% · 2 truck 11% · 3 bus 4%`, the entry matching the annotation's current class highlighted. `hidden` → nothing.

- [ ] **Step 1: Write the failing tests**

```ts
it('shows a spinner and "Predicting class…" while loading');
it('shows the top 3 with key number, name and rounded percent');
it('relabels the annotation on key 2 and pushes an undo entry');
it('ignores keys when the selected annotation is not the predicted one');
it('ignores keys typed into an input or textarea');       // Review Focus 4
it('hides on Escape');
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd lightly_studio_view && npx vitest run src/lib/components/SampleDetails/ClassPredictionStrip`
Expected: FAIL, component not found.

- [ ] **Step 3: Implement the strip**

`<svelte:window onkeydown>`; skip when `event.target` is an `input`, `textarea` or `contenteditable`, or when a modifier key is held. On relabel, also call `setAnnotationLabel` and `updateLastAnnotationLabel`, as `SampleDetailsAnnotationSegment.svelte:228-237` does after a side-panel change.

- [ ] **Step 4: Wire the call sites and mount**

Brush strokes that update a selected mask do not call `predict`. Deselecting the annotation calls `hide`.

- [ ] **Step 5: Run tests and static checks**

Run: `cd lightly_studio_view && npx vitest run src/lib/components/SampleDetails src/lib/hooks && make static-checks`
Expected: all pass, no type errors.

- [ ] **Step 6: Commit**

```bash
git add lightly_studio_view/src/lib/components/SampleDetails/ lightly_studio_view/src/lib/hooks/useSegmentationMaskBrush.ts
git commit -m "feat: show class predictions after drawing a box or mask"
```

---

### Task 7: Manual check

- [ ] **Step 1: Serve the COCO 10k box subset** (see memory `local-studio-datasets`) with a MobileCLIP collection, built from this branch (`make build-lightly_studio_view` first).
- [ ] **Step 2: Draw 20 boxes** across 3 classes, accepting the right class with 1–3 each time.
- [ ] **Step 3: Record** in the PR description: median predict latency from the browser network tab, and after how many labels per class the top 1 is right on most boxes.
- [ ] **Step 4: If zero-shot dominates too long or never helps,** adjust `TEXT_ANCHOR_WEIGHT` and note the value tried.
