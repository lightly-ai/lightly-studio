# Fix `effect_update_depth_exceeded` from Query Hooks in Reactive Contexts

## Problem

Calling query hooks (e.g. `useAnnotationLabels`) inside `$derived` creates a new `QueryObserver` on every re-run → infinite loop → `effect_update_depth_exceeded`. Moving hooks out of `$derived` locks them to initial params. Calling them in `$effect` fails because `getContext()` only works during component init.

## Solution

Make hooks accept `StoreOrVal<Params>` and pass a store to `createQuery`. This way the hook is called once at init, and the observer updates reactively via `observer.setOptions()`. A `toReadable()` utility normalizes plain objects vs stores.

**Hook pattern (before → after):**
```ts
// Before: plain object → static observer
export const useAnnotationLabels = ({ collectionId }) =>
    createQuery(readAnnotationLabelsOptions({ path: { collection_id: collectionId } }));

// After: store → reactive observer
export const useAnnotationLabels = (params: StoreOrVal<Params>) => {
    const optionsStore = derived(toReadable(params), (currentParams) =>
        readAnnotationLabelsOptions({ path: { collection_id: currentParams.collectionId } })
    );
    return createQuery(optionsStore);
};
```

**Call site pattern (before → after):**
```svelte
<!-- Before: infinite loop -->
const annotationLabels = $derived(useAnnotationLabels({ collectionId }));

<!-- After: reactive, no loop — uses toStore from svelte/store -->
const annotationLabels = useAnnotationLabels(toStore(() => ({ collectionId: collectionId ?? '' })));
```

---

## PR 1: Utility + `useHasEmbeddings` + `useEmbedText` + `useAnnotationLabels`

~80 lines. Creates the shared utility and refactors the three simplest hooks.

- [x] Create `lightly_studio_view/src/lib/utils/reactiveParams.ts` (also exports `StoreOrVal<T>` type)
- [x] Refactor `useHasEmbeddings.ts` → `StoreOrVal` + `toReadable` → `derived` → `createQuery(optionsStore)`
- [x] Refactor `useEmbedText.ts` → same pattern, preserves reactive `enabled: Boolean($p.queryText)`
- [x] Refactor `useAnnotationLabels.ts` → same pattern
- [x] Verified: `npx vitest run` — no regressions (57 file failures / 2 test failures all pre-existing)

---

## PR 2: Fix `+layout.svelte` simple hook call sites ✅

Changes in `src/routes/datasets/[dataset_id]/[collection_type]/[collection_id]/+layout.svelte`:

- [x] `useEmbedText`: `useEmbedText(toStore(() => ({ collectionId, queryText, embeddingModelId })))`
- [x] `useHasEmbeddings`: `useHasEmbeddings(toStore(() => ({ collectionId })))`
- [x] `useAnnotationLabels`: `useAnnotationLabels(toStore(() => ({ collectionId: collectionId ?? '' })))`
- [x] `useMetadataFilters`: call once at top level, `$effect` to re-trigger imperatively
- [x] `useDimensions`: same as metadataFilters + fixed to use `collectionId` directly (not `parent_collection_id`)
- [x] Verified: `svelte-check` passes with 0 errors

**Learnings for next PRs:**
- Use `toStore` from `svelte/store` (NOT `svelte/reactivity`) to convert reactive getters to stores — eliminates `writable` + `$effect` boilerplate
- Call site pattern for query hooks: `useHook(toStore(() => ({ ...reactiveParams })))`
- `useMetadataFilters` / `useDimensions` are imperative (not query hooks) — use init-once + `$effect` pattern instead

---

## PR 3: Fix conditional `annotationCounts` in `+layout.svelte`

~80 lines. Replaces the conditional hook call with three always-instantiated queries gated by `enabled`.

- [ ] Refactor `lightly_studio_view/src/lib/hooks/useAnnotationCounts/useAnnotationCounts.ts`:
  - Accept `StoreOrVal<{ collectionId, options, enabled }>` — add `enabled` field that maps to TanStack Query's `enabled` option
  - Use `toReadable` → `derived` → `createQuery(optionsStore)` pattern
- [ ] Refactor `lightly_studio_view/src/lib/hooks/useVideoAnnotationsCount/useVideoAnnotationsCount.ts` → same pattern with `enabled`
- [ ] Refactor `lightly_studio_view/src/lib/hooks/useVideoFrameAnnotationsCount/useVideoFrameAnnotationsCount.ts` → same pattern with `enabled`
- [ ] Update `+layout.svelte` (lines 222-260) — replace the conditional `$derived.by` that calls different hooks with three always-instantiated queries using `toStore` from `svelte/store`:
  ```ts
  const isVF = $derived(isVideoFrames || (isAnnotations && parentCollection?.sampleType == SampleType.VIDEO_FRAME));

  const vfQuery = useVideoFrameAnnotationCounts(toStore(() => ({ collectionId: datasetId, filter: { ... }, enabled: isVF })));
  const videoQuery = useVideoAnnotationCounts(toStore(() => ({ collectionId, filter: { ... }, enabled: isVideos && !isVF })));
  const defaultQuery = useAnnotationCounts(toStore(() => ({ collectionId: datasetId, options: { ... }, enabled: !isVF && !isVideos })));

  // Safe $derived.by — only selects which existing result to read, no hook calls
  const annotationCounts = $derived.by(() => {
      if (isVF) return vfQuery;
      if (isVideos) return videoQuery;
      return defaultQuery;
  });
  ```
- [ ] Verify: annotation counts load correctly on samples, videos, and video frames views; only the active variant fetches

---

## PR 4: Fix `Captions.svelte`

~40 lines.

- [ ] Refactor `lightly_studio_view/src/lib/hooks/useSamplesInfinite/useSamplesInfinite.ts`:
  - Accept `StoreOrVal<{ body: { filters: { collection_id, has_captions } } }>`
  - Use `toReadable` → `derived` → `createInfiniteQuery(optionsStore)`
  - For the `refresh` function: subscribe to the params store to track the latest query key so `queryClient.invalidateQueries` invalidates the right key
- [ ] Update `lightly_studio_view/src/lib/components/Captions/Captions.svelte` (lines 35-39):
  ```ts
  const { data, query, loadMore, refresh } = useSamplesInfinite(
      toStore(() => ({ body: { filters: { collection_id: parentCollectionId, has_captions: true } } }))
  );
  ```
- [ ] Verify captions load and update when navigating between collections

---

## Future PRs (same pattern, one per file)

Each ≤50 lines: refactor the hook (if not yet done) + fix the call site.

- [ ] `groups/+page.svelte` → `useGroupsInfinite`
- [ ] `frames/+page.svelte` → `useMetadataFilters`, `useVideoFramesBounds`, `useTags`
- [ ] `frames/[sample_id]/+page.svelte` → `useFrame`
- [ ] `videos/+page.svelte` → `useVideoBounds`
- [ ] `PlotPanel.svelte` → `useEmbeddings`
- [ ] `ClassifierSamplesGrid.svelte` → `useImagesInfinite`
- [ ] `AnnotationsGrid.svelte` → `useAnnotationsInfinite`
- [ ] `SampleDetailsSidePanelAnnotation.svelte` → `useAnnotationLabels` (hook already done)
- [ ] `CreateSelectionDialog.svelte` → `useTags`
- [ ] `ImageDetails.svelte` → `useImage`
- [ ] `Header.svelte` → `useCollectionWithChildren`
