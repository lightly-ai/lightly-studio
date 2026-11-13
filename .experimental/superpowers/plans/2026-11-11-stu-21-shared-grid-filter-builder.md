# STU-21: One Shared Grid Filter Builder

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the backend grid filter in one place. `imageFilter`, `buildRequestBody`, `buildVideoFilter` and `getFrameFilter` only collect their parts, and each has a complexity of 10 or less.

**Spec:** `.experimental/superpowers/specs/2026-11-11-stu-21-shared-grid-filter-builder-design.md` and the Linear issue STU-21. Read both first. The spec decides the design.

**Tech Stack:** SvelteKit, Svelte 5, TypeScript, vitest.

## Global Constraints

- Load `frontend-guide` before editing, `best-practices` for new modules, `pull-requests` before opening a PR.
- **Pin first.** In each PR, the first commit adds tests that pin the current output of the function the PR changes. They pass on the old code. The refactor commit must not change them, except the two `buildRequestBody` changes in Task 3.
- Pins compare whole outputs with `toEqual` (not `toStrictEqual`). `toEqual` ignores `undefined` keys, so an `undefined` value and a missing key are equal, as on the wire.
- Public hook APIs, stores and params types stay the same. `buildVideoFilter` and `getFrameFilter` keep returning `null` without a `collection_id`.
- The count filters change only their imports.
- Pass `embedding_region` on as it is. Never add an empty `annotations_filter`.
- Hooks import from `$lib/utils/gridFilter`, not from the `$lib/utils` barrel (the gridFilter module imports `createMetadataFilters` from `$lib/hooks/...`; the barrel risks an import cycle).
- eslint counts every `?.`, `??`, `&&` and `||`. Write `const f = params.filters ?? {}` once, not `params.filters?.x` per field.
- Complexity: `npx eslint --no-warn-ignored --rule '{"complexity":["warn",10]}' <files>` prints no `complexity` warning for the changed files.
- Checks, from `lightly_studio_view/`: `make static-checks`, `npx vitest run <files>`. Never run the full vitest suite or `make test`.
- Do not push or open PRs until the user says so. Never force-push.

## Review Focus

Each case has a pin test in the named task.

1. `imageFilter` sends annotation label IDs only; `buildRequestBody` also sends annotation `collection_ids`. Keep the difference. Task 2, `sends only annotation label ids`; Task 3, existing `propagates both annotation_label_ids and collection_ids`.
2. Videos put `annotation_frames_label_ids` in the top-level `frame_annotation_filter`, never in `sample_filter.annotations_filter`. Task 4, `puts frame labels in frame_annotation_filter`.
3. `withFilterOverrides` returns `undefined` when nothing is left, and the count filters keep sending `metadata_filters: []`. Task 5, existing `returns undefined when only removed fields remain`, and `keeps empty metadata filters` in both count-filter tests.
4. Empty label lists give no `annotations_filter` (an empty one means "has any annotation"). Task 1, `omits the annotations filter for empty lists`.
5. The frame filter still sends `frame_number: {}` without bounds, and drops a `null` or empty `video_id`. Task 4, existing `builds minimal filter with collection_id` and new `omits a null or empty video id`.

## PR Plan

All PRs are stacked. When a PR is merged, retarget the next one; do not rename branches.

| PR | Branch | Base | Tasks | Est. LOC (core / tests) |
| -- | -- | -- | -- | -- |
| 1 | `michal-stu-21-1-share-one-samplefilter-builder-across-image` | `michal-stu-23-operator-scope-label-says-filtered-when-no` | 1 (+ spec and this plan) | +90 −35 / +150 |
| 2 | `michal-stu-21-2-image-filter-builder` | PR 1 | 2 | +25 −80 / +90 |
| 3 | `michal-stu-21-3-request-body-builder` | PR 2 | 3 | +30 −55 / +90 |
| 4 | `michal-stu-21-4-video-frame-filter-builder` | PR 3 | 4 | +40 −120 / +130 |
| 5 | `michal-stu-21-5-filter-patch-helper` | PR 4 | 5 | +40 −110 / +70 |

Each PR does one thing and has under 100 core lines. PR 4 changes two functions, but both are small and use the builder the same way. Do the manual check (Task 6) before opening each PR.

## Folder `lightly_studio_view/src/lib/utils/gridFilter/`

| File | Contents | Task |
| -- | -- | -- |
| `getAnnotationsFilter.ts` (+ test) | moved with `git mv` from `hooks/useImagesInfinite/` | 1 |
| `withoutUndefined.ts` | private helper, not in the barrel | 1 |
| `buildSampleFilter.ts` (+ test) | `buildSampleFilter`, `toMetadataFilters` | 1 |
| `ranges.ts` (+ test) | `toRange`, `dimensionRanges` | 1 |
| `buildGridFilter.ts` (+ test) | `buildGridFilter` | 1 |
| `withFilterOverrides.ts` (+ test) | moved with `git mv` from `utils/` | 5 |
| `patchFilters.ts` (+ test) | `patchFilters` | 5 |
| `index.ts` | barrel of the public names | 1, 5 |

---

### Task 1: Shared builder helpers (PR 1)

**Files:**
- Create: the Task 1 files in the folder table.
- Move: `hooks/useImagesInfinite/getAnnotationsFilter.ts` and its test into `gridFilter/`; update the import in `buildRequestBody.ts:4`.
- Modify: `utils/withFilterOverrides.ts` (delete `imageDimensionRanges`), `utils/withFilterOverrides.test.ts` (move its two `imageDimensionRanges` tests to `ranges.test.ts`), `utils/index.ts:52`, `R/imageAnnotationCountsFilter.ts:3,30` (import and call `dimensionRanges`). `R` = `src/routes/datasets/[dataset_id]/[collection_type]/[collection_id]`.

**Interfaces:**
- Produces:
  - `withoutUndefined<T extends object>(value: T): Partial<T>` — copy without keys whose value is `undefined`. Keeps `null` and `[]`.
  - `type SampleFilterParts = { sample_ids?: string[] | null; tag_ids?: string[] | null; annotation_label_ids?: string[] | null; annotation_collection_ids?: string[] | null; embedding_region?: EmbeddingRegion | null; confusion_cell?: ConfusionCell | null; metadata_filters?: MetadataFilter[] | null; query_expr?: QueryExpr | null }`
  - `buildSampleFilter(parts: SampleFilterParts): SampleFilter | undefined` — empty lists and `null` become missing keys; `annotations_filter = getAnnotationsFilter({ annotation_label_ids, collection_ids: annotation_collection_ids })`; `undefined` when no key is left. Use a private `nonEmpty(list)` for the four lists.
  - `toMetadataFilters(metadataValues?: MetadataValues, categoricalValues?: CategoricalMetadataValues): MetadataFilter[] | undefined` — `undefined` when both are missing, else `createMetadataFilters(metadataValues ?? {}, categoricalValues ?? {})`. Replaces the four copies of this check.
  - `toRange(range: { min?: number | null; max?: number | null } | null | undefined): FilterDimensions | undefined` — `{ min: range.min ?? undefined, max: range.max ?? undefined }`.
  - `dimensionRanges(bounds: DimensionBounds | null | undefined): { width: FilterDimensions | undefined; height: FilterDimensions | undefined }` — always both keys (the counts filter relies on present-but-`undefined` keys to remove width and height).
  - `type GridFilterByType = { image: ImageFilter; video: VideoFilter; video_frame: VideoFrameFilter }`
  - `buildGridFilter<T extends keyof GridFilterByType>(filterType: T, fields: Omit<GridFilterByType[T], 'filter_type' | 'sample_filter'>, sampleFilter: SampleFilter | undefined): GridFilterByType[T] & { filter_type: T }` — `filter_type` + `withoutUndefined(fields)` + `sample_filter` only when defined.
  - `gridFilter/index.ts` exports all of the above except `withoutUndefined`. `utils/index.ts` re-exports `dimensionRanges` in place of `imageDimensionRanges`.

`REGION = { polygon: [{ x: 0, y: 0 }, { x: 1, y: 0 }, { x: 0, y: 1 }] }`, `CELL = { evaluation_run_id: 'run-1', gt_label: 'car', pred_label: 'truck' }`.

- [ ] **Step 1: Write the failing tests:**
  - `buildSampleFilter`: `returns undefined for no parts`; `returns undefined when every list is empty` (all four lists `[]`, `metadata_filters: []`); `omits the annotations filter for empty lists` (`annotation_label_ids: [], annotation_collection_ids: []`, `tag_ids: ['t']` → `{ tag_ids: ['t'] }`); `builds the annotations filter from labels and collections` (`{ filter_type: 'annotations', annotation_label_ids: ['l'], collection_ids: ['c'] }`); `passes the embedding region through unchanged` (`toBe(REGION)`); `drops null values` (region, cell, query `null` → `undefined`); `keeps every set part` (all parts set → each key once).
  - `toMetadataFilters`: `returns undefined without values`; `calls createMetadataFilters when either is set` (mock it, check args `({a}, {})` and `({}, {b})`).
  - `toRange`: `undefined` → `undefined`; `{ min: null, max: 5 }` → `{ min: undefined, max: 5 }`; `{ min: 1, max: 2 }` → same.
  - `dimensionRanges`: the two moved tests, plus `has both keys for null bounds` (`'width' in result`).
  - `buildGridFilter`: `sets only the filter type when empty` (`('image', {}, undefined)` → `{ filter_type: 'image' }`); `omits undefined fields but keeps null and {}` (`frame_number: {}` kept); `adds sample_filter only when defined`.
- [ ] **Step 2: Run** `npx vitest run src/lib/utils/gridFilter` — FAIL (modules missing).
- [ ] **Step 3: Implement** the functions; do the moves and import updates.
- [ ] **Step 4: Run** the folder, `src/lib/utils/withFilterOverrides.test.ts`, `src/lib/hooks/useImagesInfinite/buildRequestBody.test.ts`, `R/imageAnnotationCountsFilter.test.ts` — PASS. `grep -rn imageDimensionRanges src` is empty. `make static-checks` — PASS.
- [ ] **Step 5: Commit** `Add the shared grid filter helpers`.

### Task 2: `imageFilter` in `useImageFilters` (PR 2)

**Files:** Modify `src/lib/hooks/useImageFilters/useImageFilters.ts:18-40,49-126`, `useImageFilters.test.ts`.

**Interfaces:** Consumes `buildGridFilter`, `buildSampleFilter`, `toMetadataFilters`, `dimensionRanges` (Task 1).

- [ ] **Step 1: Pin the current output** in a new `describe('imageFilter output')`. Use `mockReturnValueOnce([M])` on the mocked `createMetadataFilters` where metadata is set.
  - `returns null without a collection id`; `returns null in classifier mode`.
  - `returns only the filter type when nothing is set` → `{ filter_type: 'image' }`.
  - `pins every field`: dimensions `{ min_width: 1, max_width: 2, min_height: 3, max_height: 4 }`, `sample_ids: ['s']`, `embedding_region: REGION`, `annotation_label_ids: ['l']`, `tag_ids: ['t']`, `confusion_cell: CELL`, `metadata_values` set, query expression set → `{ filter_type: 'image', width: { min: 1, max: 2 }, height: { min: 3, max: 4 }, sample_filter: { sample_ids, embedding_region, annotations_filter: { filter_type: 'annotations', annotation_label_ids: ['l'] }, tag_ids, confusion_cell, metadata_filters: [M], query_expr } }`.
  - `drops empty lists`: all lists `[]`, metadata mock `[]` → `{ filter_type: 'image' }`.
  - `sends only annotation label ids`: `annotation_label_ids: ['l'], collection_ids: ['c']` → `annotations_filter` without `collection_ids`.
  - `passes categorical-only metadata`: only `categorical_metadata_values: C` (top level of the params), mock returns `[M]` once → `createMetadataFilters` called with `({}, C)`, and `sample_filter.metadata_filters` is `[M]`.
- [ ] **Step 2: Run** `npx vitest run src/lib/hooks/useImageFilters/useImageFilters.test.ts` — PASS on the old code. **Commit** `Pin the image filter output`.
- [ ] **Step 3: Refactor.** `imageFilter` returns `null` unless `collection_id` is set and `mode === 'normal'`, then `buildGridFilter('image', dimensionRanges(f.dimensions), buildSampleFilter({ ... }))` with no `annotation_collection_ids`. Keep the LIG-9903 comment next to `embedding_region`. Delete `buildFilterDimensions`, `extractDimensions` and the final `null` check.
- [ ] **Step 4: Run** the test file, `make static-checks`, and the complexity command on `useImageFilters.ts` — PASS, no warning.
- [ ] **Step 5: Commit** `Build the image filter with the shared builder`.

### Task 3: `buildRequestBody` (PR 3)

**Files:** Modify `src/lib/hooks/useImagesInfinite/buildRequestBody.ts`, `buildRequestBody.test.ts`.

**Interfaces:** Consumes `buildSampleFilter`, `toMetadataFilters`, `dimensionRanges`. `buildRequestBody(params, pageParam): ReadImagesRequest` keeps its signature.

- [ ] **Step 1: Pin the current output** (whole body, `toEqual`):
  - `pins every normal-mode field`: all `NormalModeFilters` fields, including `collection_ids`, plus `query_expr`, `metadata_values`, `sort_by`, `text_embedding` → exact body; `annotations_filter` has both label and collection IDs.
  - `pins the classifier body`: samples, `query_expr` and `metadata_values` → `sample_ids` = positives then negatives; `sample_filter` has only `query_expr` and `metadata_filters`; no width or height.
  - `sends empty sample ids for empty classifier lists`: `classifierSamples: { positiveSampleIds: [], negativeSampleIds: [] }` → `sample_ids: []`.
  - `sends no sample ids without classifier samples`: classifier mode, no `classifierSamples` → no `sample_ids` key (`'sample_ids' in body` is false).
  - `passes categorical-only metadata`: only `categorical_metadata_values: C`, mock returns `[M]` once → `createMetadataFilters` called with `({}, C)`, and `sample_filter.metadata_filters` is `[M]`.
- [ ] **Step 2: Run** the test file — PASS on the old code. **Commit** `Pin the image request body`.
- [ ] **Step 3: Write the failing tests** for the two wire changes the spec allows:
  - `sends no sample filter when nothing is set`: `{ collection_id, mode: 'normal' }` → `filters` equals `{}`.
  - `sends no empty metadata filters`: `metadata_values: {}` with the mock returning `[]` once → `filters.sample_filter` is `undefined`.
- [ ] **Step 4: Run** — the two new tests FAIL.
- [ ] **Step 5: Refactor.** The body is `pagination`, `text_embedding`, `sort_by`, `sample_ids` (only in classifier mode with `classifierSamples`; otherwise no key) and `filters = { ...dimensionRanges(f.dimensions), sample_filter: buildSampleFilter({ ...normal-mode parts, annotation_collection_ids: f.collection_ids, query_expr, metadata_filters: toMetadataFilters(...) }) }`, where `f` is the normal-mode filters or `{}`. Delete `buildBaseBody`, `withClassifierSamples`, `withNormalFilters` and the TODO (closed). Keep the LIG-9903 comment.
- [ ] **Step 6: Run** the test file, `useImagesInfinite.test.ts`, `createImagesInfiniteOptions.test.ts`, `make static-checks`, the complexity command — PASS, no warning.
- [ ] **Step 7: Commit** `Build the image request body with the shared builder`.

### Task 4: `buildVideoFilter` and `getFrameFilter` (PR 4)

**Files:** Modify `src/lib/hooks/useVideoFilters/useVideoFilters.ts:30-108`, `useVideoFilters.test.ts`, `src/lib/hooks/useFramesFilter/frameFilter.ts:24-80`, `frameFilter.test.ts`.

**Interfaces:** Consumes `buildGridFilter`, `buildSampleFilter`, `toMetadataFilters`, `toRange`, `getAnnotationsFilter`. Signatures of `buildVideoFilter` and `getFrameFilter` stay.

- [ ] **Step 1: Pin the current output:**
  - Bounds use `IntRange`, whose `min` and `max` are required numbers, so use plain numbers. The `toRange` tests (Task 1) cover `null` bounds.
  - Video: `pins every field` (bounds `width: { min: 1, max: 9 }` → same, `fps` and `duration_s` passed through as-is, tags, sample ids, region, metadata, frame labels → exact filter); `returns only the filter type when nothing is set`; `drops empty lists`; `puts frame labels in frame_annotation_filter`: `annotation_frames_label_ids: ['l'], tag_ids: ['t']` → `{ filter_type: 'video', frame_annotation_filter: { filter_type: 'annotations', annotation_label_ids: ['l'] }, sample_filter: { tag_ids: ['t'] } }`.
  - Frame: `pins every field` (`video_id`, `frame_number: { min: 0, max: 9 }`, labels in `sample_filter.annotations_filter`, tags, sample ids, metadata); `drops empty lists`; `omits a null or empty video id` (`null` and `''` → no `video_id`).
  - Both: `passes categorical-only metadata` (only `filters.categorical_metadata_values: C`, mock returns `[M]` once) → `createMetadataFilters` called with `({}, C)`, and `sample_filter.metadata_filters` is `[M]`.
- [ ] **Step 2: Run** both test files — PASS on the old code. **Commit** `Pin the video and frame filter output`.
- [ ] **Step 3: Refactor.**
  - `buildVideoFilter`: `buildGridFilter('video', { ...videoBoundsFields(params.video_bounds), frame_annotation_filter: getAnnotationsFilter({ annotation_label_ids: f.annotation_frames_label_ids }) }, buildSampleFilter({ ... }))`. Private `videoBoundsFields(bounds: VideoFieldsBoundsView | null | undefined): Pick<VideoFilter, 'width' | 'height' | 'fps' | 'duration_s'>` — `{}` for no bounds, `toRange` for width and height.
  - `getFrameFilter`: `buildGridFilter('video_frame', { video_id: params.video_id || undefined, frame_number: toRange(params.frame_bounds?.frame_number) ?? {} }, buildSampleFilter({ ... }))`.
- [ ] **Step 4: Run** both test files, `useFramesFilter.test.ts`, `src/lib/hooks/useSelectAll`, `R/VideoDistributionPanel/videoDistributionFilters.test.ts`, `make static-checks`, the complexity command on both files — PASS, no warning.
- [ ] **Step 5: Commit** `Build the video and frame filters with the shared builder`.

### Task 5: `patchFilters` and `withFilterOverrides` (PR 5)

**Files:**
- Create: `gridFilter/patchFilters.ts`, `.test.ts`.
- Move: `utils/withFilterOverrides.ts` and its test into `gridFilter/` with `git mv`; update `utils/index.ts:52` and `gridFilter/index.ts`.
- Modify: setters in `useImageFilters.ts:145-206`, `useVideoFilters.ts:127-156`; `R/imageAnnotationCountsFilter.test.ts`, `R/videoAnnotationCountsFilter.test.ts`.

**Interfaces:**
- Produces: `patchFilters<P extends { filters?: object }>(params: P, patch: Partial<NonNullable<P['filters']>>): P` — `{ ...params, filters: { ...params.filters, ...patch } }`. Keeps `undefined` values as keys, as the setters do today.
- `withFilterOverrides` keeps its signature. Each level is `withoutUndefined({ ...base, ...overrides })`. A `sample_filter` override is always applied key by key; delete the `sample_filter: undefined` branch.

- [ ] **Step 1: Pin:**
  - `imageAnnotationCountsFilter.test.ts` and `videoAnnotationCountsFilter.test.ts`: `keeps empty metadata filters` (`metadataFilters: []` → `sample_filter: { metadata_filters: [] }`).
  - `useImageFilters.test.ts`: `updateSampleIds does nothing in classifier mode`; `updateSampleIds clears sample ids for an empty list`; `updateEmbeddingRegion stores and clears the region` (`toBe(REGION)` while set).
- [ ] **Step 2: Run** those files and `withFilterOverrides.test.ts` — PASS on the old code. **Commit** `Pin the filter setters and count filters`.
- [ ] **Step 3: Write the failing `patchFilters` tests:** `merges the patch into filters`; `creates filters when missing`; `keeps undefined values as keys`; `does not mutate params`.
- [ ] **Step 4: Run** — FAIL (module missing).
- [ ] **Step 5: Implement.** Each setter keeps its guard (images: `mode === 'normal'`; videos: `collection_id`) and calls `filterParams.set(patchFilters(params, { ... }))`. Move and simplify `withFilterOverrides`.
- [ ] **Step 6: Run** the `gridFilter` folder, both hook tests, both count-filter tests, `R/ImageDistributionPanel/distributionBaseFilter.test.ts`, `R/VideoDistributionPanel/videoDistributionFilters.test.ts`, `make static-checks`, the complexity command on all files in this plan — PASS, no warning. The existing `returns undefined when only removed fields remain` still passes.
- [ ] **Step 7: Commit** `Share one patch helper across the filter setters`.

### Task 6: Manual checks (each PR)

Start the app with the `run` skill. In the browser network tab, compare request bodies with the base branch.

- [ ] PR 1: image class counts still change with the dimension slider.
- [ ] PR 2: images grid with a tag, a label, a metadata range and a lasso selection: grid, counts and operator scope match the base branch.
- [ ] PR 3: same grid; the `/images/list` body is the same except no `sample_filter: {}` and no `metadata_filters: []`. Classifier mode still loads.
- [ ] PR 4: videos grid with frame labels, an fps range and a lasso; frames grid with a frame-number range and a single-video view. Bodies match.
- [ ] PR 5: lasso, sample-id selection and confusion cell set and clear on images; lasso on videos. Class counts and distributions still follow the selection.
