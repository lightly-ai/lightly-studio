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

## PR 1: Utility + `useHasEmbeddings` + `useEmbedText` + `useAnnotationLabels` ✅

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

## PR 3: All remaining hooks → StoreOrVal ✅

Converted all 11 remaining query hooks to accept `StoreOrVal` parameters. This was done in a single PR instead of incremental per-file PRs (deviation from original plan).

- [x] `useAnnotationCounts` — added `enabled` flag
- [x] `useAnnotationsInfinite`
- [x] `useCollection`
- [x] `useCollectionWithChildren`
- [x] `useEmbeddings`
- [x] `useFrame`
- [x] `useGroupsInfinite`
- [x] `useImage`
- [x] `useImagesInfinite`
- [x] `useSamplesInfinite`
- [x] `useVideoAnnotationsCount` — added `enabled` flag
- [x] `useVideoFrameAnnotationsCount` — added `enabled` flag

---

## PR 4: All call sites ✅

Updated 18 components to use `toStore(() => ...)` pattern and removed `$derived` wrappers. This was done in a single PR instead of incremental per-file PRs.

- [x] Refactored conditional `annotationCounts` in `+layout.svelte` to three always-instantiated queries gated by `enabled`
- [x] Updated all query hook call sites across 18 components
- [x] Verified: `svelte-check` — 0 errors, 0 warnings

---

## Remaining Work

3 files still have `$derived` wrapping **imperative** (non-query) hooks:

| File | Hook | Line |
|------|------|------|
| `CreateSelectionDialog.svelte` | `useTags` | `$derived(useTags({...}))` |
| `frames/+page.svelte` | `useMetadataFilters` | `$derived(useMetadataFilters(...))` |
| `frames/+page.svelte` | `useVideoFramesBounds` | `$derived(useVideoFramesBounds(...))` |
| `videos/+page.svelte` | `useVideoBounds` | `$derived.by(() => useVideoBounds(...))` |

These 4 hooks are **imperative** (not TanStack Query). They init data on first call and return stores/functions. The fix follows the same pattern used in PR2's layout for `useMetadataFilters`/`useDimensions`: call once at init, use `$effect` to re-trigger when params change.

### PR5: Fix remaining imperative hook call sites (~40 LOC)

**`src/lib/components/Selection/CreateSelectionDialog.svelte`:**
```ts
// Before:
const { loadTags } = $derived(useTags({ collection_id: collectionId, kind: ['sample'] }));
// After:
const { loadTags } = useTags({ collection_id: collectionId, kind: ['sample'] });
$effect(() => { loadTags(); });
```

**`src/routes/.../frames/+page.svelte`:**
```ts
// Before:
const { metadataValues } = $derived(useMetadataFilters(collectionId));
const { videoFramesBoundsValues } = $derived(useVideoFramesBounds(collectionId));
// After:
const { metadataValues } = useMetadataFilters(collectionId);
const { videoFramesBoundsValues } = useVideoFramesBounds(collectionId);
```

**`src/routes/.../videos/+page.svelte`:**
```ts
// Before:
const { videoBoundsValues } = $derived.by(() => useVideoBounds(collectionId));
// After:
const { videoBoundsValues } = useVideoBounds(collectionId);
```
