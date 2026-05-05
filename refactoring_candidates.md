# Refactoring Shortlist — Split by Stack

Each item is self-contained: read the description and you know what's wrong, what you'd gain, and where to look.

Source links are pinned to commit [`43ff45b`](https://github.com/lightly-ai/lightly-studio/tree/43ff45b) so line numbers stay valid even as `main` moves on.

---

## Frontend (`lightly_studio_view/`)

### F1. Four near-identical "dialog open/close" hooks

**Problem.** We have four hooks that each declare a module-level `writable(false)` and expose `openX` / `closeX` setters: `useSettingsDialog`, `useExportDialog`, `useSelectionDialog`, `useOperatorsDialog`. They are 19 lines each and differ only in the dialog name. New dialogs are likely to copy this pattern again.

**Gain.** Replace with a small `createDialogStore('settings')` factory. ~70 lines collapse to ~15 plus four one-liners. New dialogs become a single line. The shape of every dialog's state is enforced.

**Where.**

- [`useSettingsDialog.ts`](https://github.com/lightly-ai/lightly-studio/blob/43ff45b/lightly_studio_view/src/lib/hooks/useSettingsDialog/useSettingsDialog.ts)
- [`useExportDialog.ts`](https://github.com/lightly-ai/lightly-studio/blob/43ff45b/lightly_studio_view/src/lib/hooks/useExportDialog/useExportDialog.ts)
- [`useSelectionDialog.ts`](https://github.com/lightly-ai/lightly-studio/blob/43ff45b/lightly_studio_view/src/lib/hooks/useSelectionDialog/useSelectionDialog.ts)
- [`useOperatorsDialog.ts`](https://github.com/lightly-ai/lightly-studio/blob/43ff45b/lightly_studio_view/src/lib/hooks/useOperatorsDialog/useOperatorsDialog.ts)

---

### F2. Repeated promise-wrapper around tanstack mutations

**Problem.** Seven mutation hooks all do the same dance: build a tanstack `createMutation`, call `mutation.subscribe(() => undefined)` to force callbacks to fire, then wrap `.mutate(...)` in a `new Promise((resolve, reject) => ...)` so callers can `await` it. Notably, the comment "We need to have this subscription to get onSuccess/onError events" is copy-pasted verbatim across files — that's a strong sign a missing abstraction has spread.

**Gain.** A single helper (e.g. `createPromiseMutation(factory, { onSuccess })`) centralises the awkward subscribe-workaround so it's documented in one place, makes new mutation hooks 5 lines instead of 30, and prevents future drift between hooks. If we ever want to handle errors uniformly (toasts, logging), there's one place to do it.

**Where.**

- [`useCreateAnnotation.ts:11-47`](https://github.com/lightly-ai/lightly-studio/blob/43ff45b/lightly_studio_view/src/lib/hooks/useCreateAnnotation/useCreateAnnotation.ts#L11-L47)
- [`useDeleteAnnotation.ts:6-44`](https://github.com/lightly-ai/lightly-studio/blob/43ff45b/lightly_studio_view/src/lib/hooks/useDeleteAnnotation/useDeleteAnnotation.ts#L6-L44)
- [`useCreateCaption.ts:7-33`](https://github.com/lightly-ai/lightly-studio/blob/43ff45b/lightly_studio_view/src/lib/hooks/useCreateCaption/useCreateCaption.ts#L7-L33)
- [`useDeleteCaption.ts:5-33`](https://github.com/lightly-ai/lightly-studio/blob/43ff45b/lightly_studio_view/src/lib/hooks/useDeleteCaption/useDeleteCaption.ts#L5-L33)
- [`useCreateLabel.ts:9-38`](https://github.com/lightly-ai/lightly-studio/blob/43ff45b/lightly_studio_view/src/lib/hooks/useCreateLabel/useCreateLabel.ts#L9-L38)
- [`useRemoveTagFromSample.ts:5-31`](https://github.com/lightly-ai/lightly-studio/blob/43ff45b/lightly_studio_view/src/lib/hooks/useRemoveTagFromSample/useRemoveTagFromSample.ts#L5-L31)
- [`useUpdateAnnotationsMutation.ts:7-44`](https://github.com/lightly-ai/lightly-studio/blob/43ff45b/lightly_studio_view/src/lib/hooks/useUpdateAnnotationsMutation/useUpdateAnnotationsMutation.ts#L7-L44)

---

### F3. Image and video embedding-filter hooks duplicate structure

**Problem.** Both hooks build an `activeSampleIds` derived store from a filter source and pass it to `useFilterVisibility(...)`. The only meaningful differences are which filter hook they read from (`useImageFilters` vs `useVideoFilters`) and one image-only guard (`isNormalModeParams`). If someone changes embedding-filter behavior on one path, the other will silently drift.

**Gain.** A generic `useEmbeddingFilter(filtersHook, options)` keeps image and video paths in lockstep. Same surface area, lower divergence risk.

**Where.**

- [`useEmbeddingFilterForImages.ts`](https://github.com/lightly-ai/lightly-studio/blob/43ff45b/lightly_studio_view/src/lib/hooks/useEmbeddingFilter/useEmbeddingFilterForImages.ts)
- [`useEmbeddingFilterForVideos.ts`](https://github.com/lightly-ai/lightly-studio/blob/43ff45b/lightly_studio_view/src/lib/hooks/useEmbeddingFilter/useEmbeddingFilterForVideos.ts)

---

### F4. Positive/negative sample-id split repeats inside `useClassifiers.ts`

**Problem.** A 6-line block that computes "all sample IDs → positive set → negative = all minus positive" appears at least twice in `useClassifiers.ts` (in `createClassifier` around line 167 and in `refineClassifier` lower in the file). This is the kind of logic that tends to silently get out-of-sync as one branch is updated and the other isn't.

**Gain.** Pull into a single `getAnnotatedSamplePartition()` returning `{ positive, negative }`. Removes ~12 lines, removes the foot-gun, and clarifies what each call site actually needs from classifier samples.

**Where.** [`useClassifiers.ts:167-179`](https://github.com/lightly-ai/lightly-studio/blob/43ff45b/lightly_studio_view/src/lib/hooks/useClassifiers/useClassifiers.ts#L167-L179) (and the matching block lower in the same file).

---

### F5. Six-branch `if/else` chain to map a route to a grid type

**Problem.** Inside the dataset-route layout, an `$effect` walks through `if (isAnnotations) … else if (isImages) … else if (isCaptions) …` over six route flags to set `gridType`. The flags are themselves derived from the same route, so we're pattern-matching the route twice in two different shapes.

**Gain.** Replace with a `$derived` computed from a single `route → gridType` lookup table. Adding a new collection type becomes a one-line entry instead of a new `else if`. Makes the layout file noticeably shorter.

**Where.** [`+layout.svelte:153-184`](https://github.com/lightly-ai/lightly-studio/blob/43ff45b/lightly_studio_view/src/routes/datasets/%5Bdataset_id%5D/%5Bcollection_type%5D/%5Bcollection_id%5D/+layout.svelte#L153-L184).

---

### F6. Components that take wide objects when they read only a few fields

**Problem.** Some components accept large backend types (e.g. `MenuDialogHost.svelte` takes a full `CollectionView` but only reads `sample_type`; `SampleDetailsPanel.svelte` declares 11 props including a full `sample` object but uses only a handful of fields). This couples the component to the schema and bloats test fixtures.

**Gain.** Narrow each prop type to exactly what the component reads. Tests become trivial to set up; if the backend type changes a field the component doesn't use, the component doesn't need to be touched. Pure win, low risk per component, but spread across many components — best done incrementally.

**Where.**

- [`MenuDialogHost.svelte`](https://github.com/lightly-ai/lightly-studio/blob/43ff45b/lightly_studio_view/src/lib/components/Header/MenuDialogHost.svelte)
- [`SampleDetailsPanel.svelte:46-67`](https://github.com/lightly-ai/lightly-studio/blob/43ff45b/lightly_studio_view/src/lib/components/SampleDetails/SampleDetailsPanel.svelte#L46-L67)

Likely more — worth grepping for `: CollectionView` and `: SampleView` in component props.

---

## Backend (`lightly_studio/`)

### B1. Two resolver helpers are byte-identical across files

**Problem.** `_compute_next_cursor` and the eager-load chain `_get_load_options` for the `sample` relationship appear in both `image_resolver/get_all_by_collection_id.py` and `video_resolver/get_all_by_collection_id.py`. The pagination helper is byte-identical; the eager-load tree (tags, captions, annotations + label + object detection + segmentation) is the same shape on both sides.

**Gain.** Move both into a shared module (e.g. `resolvers/_common.py`). Eliminates a real duplication, prevents the two cursors from drifting, and gives us one place to add eager-loaded relationships in the future. Mechanical refactor.

**Where.**

- [`image_resolver/get_all_by_collection_id.py:35-58`](https://github.com/lightly-ai/lightly-studio/blob/43ff45b/lightly_studio/src/lightly_studio/resolvers/image_resolver/get_all_by_collection_id.py#L35-L58)
- [`video_resolver/get_all_by_collection_id.py:32-76`](https://github.com/lightly-ai/lightly-studio/blob/43ff45b/lightly_studio/src/lightly_studio/resolvers/video_resolver/get_all_by_collection_id.py#L32-L76)

---

### B2. Parallel annotation processors (segmentation vs object-detection)

**Problem.** Two pairs of functions mirror each other:

- [`add_images.py:444-487`](https://github.com/lightly-ai/lightly-studio/blob/43ff45b/lightly_studio/src/lightly_studio/core/image/add_images.py#L444-L487) — `_process_object_detection_annotations` and `_process_segmentation_annotations` iterate `anno_data.data.objects` and call a labelformat helper per object.
- [`add_videos.py:555-596`](https://github.com/lightly-ai/lightly-studio/blob/43ff45b/lightly_studio/src/lightly_studio/core/video/add_videos.py#L555-L596) — `_process_video_annotations_segmentation_mask` and `_process_video_annotations_object_detection` do the same thing per video frame.

In each pair, only the field read off the object (`box` vs `segmentation`) and the helper called differ. The control flow is identical.

**Gain.** Replace each pair with one function that takes a per-object converter callable. Halves the number of functions to maintain and makes it impossible for one annotation type's loop to accidentally drift from the other's. Also makes it easier to add a third annotation type later.

**Where.** Lines above. Two small refactors, do them together for consistency.

---

### B3. `add_images.py` and `add_videos.py` mix many responsibilities

**Problem.** Both files are over 500 lines and each does several things: path-based loading, labelformat-based loading, COCO captions loading (image side), frame extraction (video side), tagging, batch annotation processing, and per-format annotation processors. There is also an existing TODO around cloud-path support that's blocked by how tangled the file is.

**Gain.** Split each into a small package by responsibility (e.g. `core/image/loaders/from_paths.py`, `from_labelformat.py`, `from_coco_captions.py`, `_batch.py`). Smaller files are easier to test in isolation, future format additions become new files instead of inflating an existing one, and the cloud-path change becomes a localized edit rather than a rewrite.

**Where.**

- [`core/image/add_images.py`](https://github.com/lightly-ai/lightly-studio/blob/43ff45b/lightly_studio/src/lightly_studio/core/image/add_images.py) (556 lines)
- [`core/video/add_videos.py`](https://github.com/lightly-ai/lightly-studio/blob/43ff45b/lightly_studio/src/lightly_studio/core/video/add_videos.py) (596 lines)

---

### B4. `_build_export_query` is a 152-line branchy query builder

**Problem.** The function is marked `# noqa: C901` (cyclomatic complexity exceeded) and has separate large branches for each filter type (`include.tag_ids`, `include.sample_ids`, `include.annotation_ids`, and the `exclude` mirror). Reading it requires holding several SQL fragments in your head at once.

**Gain.** Extract one helper per filter type (`_query_for_tag_ids`, `_query_for_sample_ids`, …). The top-level function becomes a small dispatcher that's easy to scan and easy to extend. Each helper is independently testable.

**Where.** [`resolvers/collection_resolver/export.py:136-287`](https://github.com/lightly-ai/lightly-studio/blob/43ff45b/lightly_studio/src/lightly_studio/resolvers/collection_resolver/export.py#L136-L287).

---

### B5. `ClassifierManager` does too many things

**Problem.** `few_shot_classifier/classifier_manager.py` is 667 lines in a single class that handles classifier lifecycle (create / update / delete), training, the annotation buffer, and export. Changes to one concern often require reading/touching the others to be confident nothing breaks.

**Gain.** Split into focused collaborators (e.g. `ClassifierLifecycle`, `ClassifierTrainer`, `ClassifierExporter`) using composition. Each piece becomes <300 lines, has a narrower public surface, and is testable without spinning up the whole manager. Makes it tractable for someone new to the area to make a change.

**Where.** [`few_shot_classifier/classifier_manager.py`](https://github.com/lightly-ai/lightly-studio/blob/43ff45b/lightly_studio/src/lightly_studio/few_shot_classifier/classifier_manager.py).

---

### B6. Long monolithic loader functions

**Problem.** `load_into_collection_from_paths` (~119 lines) and `load_video_annotations_from_labelformat` (~123 lines) each interleave several concerns inside one function — opening the video stream, reading metadata, creating samples, extracting frames, error handling. Same on the image side: `load_into_dataset_from_labelformat` and `load_into_dataset_from_coco_captions`.

**Gain.** Extract per-step helpers (e.g. `_open_video_stream(path)`, `_create_video_sample(...)`, `_process_single_video(...)`). The top-level then reads as 4-5 named calls — anyone reading it can understand the high-level flow without tracking nested try/except. Mostly a side-effect of doing B3, but worth flagging as the most painful examples.

**Where.**

- [`add_videos.py:78-196`](https://github.com/lightly-ai/lightly-studio/blob/43ff45b/lightly_studio/src/lightly_studio/core/video/add_videos.py#L78-L196) — `load_into_collection_from_paths`
- [`add_videos.py:199-321`](https://github.com/lightly-ai/lightly-studio/blob/43ff45b/lightly_studio/src/lightly_studio/core/video/add_videos.py#L199-L321) — `load_video_annotations_from_labelformat`
- [`add_images.py:145-240`](https://github.com/lightly-ai/lightly-studio/blob/43ff45b/lightly_studio/src/lightly_studio/core/image/add_images.py#L145-L240) — `load_into_dataset_from_labelformat`
- [`add_images.py:243-342`](https://github.com/lightly-ai/lightly-studio/blob/43ff45b/lightly_studio/src/lightly_studio/core/image/add_images.py#L243-L342) — `load_into_dataset_from_coco_captions`

---

### B7. Loader entry points share a skeleton

**Problem.** The `load_into_dataset_from_*` and `load_into_collection_from_*` functions (paths / labelformat / coco_captions) all repeat the same outline: filter new paths → build `LoadingLoggingContext` → `tqdm` loop → call `create_many` → `log_loading_results`. Lower priority than B2/B6 because the per-format bodies are genuinely different, but the surrounding scaffolding is identical.

**Gain.** A `LoadingPipeline` helper that takes a per-item processor would remove ~10 lines of boilerplate per loader and make the format-specific logic the focus of each function. Best done after B3 splits the files; the pattern is more obvious then.

**Where.** Top of each loader function in [`add_images.py`](https://github.com/lightly-ai/lightly-studio/blob/43ff45b/lightly_studio/src/lightly_studio/core/image/add_images.py) and [`add_videos.py`](https://github.com/lightly-ai/lightly-studio/blob/43ff45b/lightly_studio/src/lightly_studio/core/video/add_videos.py).

---

## Suggested order if you want one PR per item

**Frontend, easiest first:** F1 (dialog factory) → F4 (sample-id helper) → F5 (route-to-grid map) → F2 (mutation helper, touches more files but uniform) → F3 (embedding filter unify) → F6 (prop narrowing, incremental).

**Backend, easiest first:** B1 (resolver helpers) → B2 (annotation processors) → B4 (export query) → B3 (split image/video loader files) → B6 (long loader extractions, falls out of B3) → B7 (pipeline helper) → B5 (ClassifierManager split, biggest).
