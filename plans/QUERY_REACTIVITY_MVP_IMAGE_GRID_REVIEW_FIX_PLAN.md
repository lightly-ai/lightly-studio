# Query Reactivity MVP: Review Fix Plan (Steps 1-4 Follow-Up)

## Objective

Address review findings from the uncommitted MVP implementation while preserving the Step 1-4 goal: stable group -> images navigation without `effect_update_depth_exceeded`.

## Scope

In scope:

- fix functional regressions flagged in review (P1)
- remove temporary debug logging
- perform targeted style/maintainability cleanup (P2)
- validate with focused manual and automated checks

Out of scope:

- broader Phase 2/3 refactor from `QUERY_REACTIVITY_REFACTOR_PLAN.md`
- unrelated route/hook migrations not required by these findings

## Checklist

## 1) Restore intended sample-selection reset behavior (P1)

File: `lightly_studio_view/src/routes/datasets/[dataset_id]/[collection_type]/[collection_id]/+layout.svelte`

- [ ] Decide and document intended behavior for grid transitions in the same collection:
  - Option A (recommended): clear selected samples when `gridType` changes (previous behavior).
  - Option B: keep selection across grids and explicitly clear `sample_ids` when entering images.
- [ ] Implement chosen behavior so stale `sample_ids` do not leak into image queries after groups -> images navigation.
- [ ] Add/update a short comment describing the chosen reset rule.

## 2) Make collection-dependent hooks react to route param changes (P1)

Files:

- `lightly_studio_view/src/routes/datasets/[dataset_id]/[collection_type]/[collection_id]/+layout.svelte`
- `lightly_studio_view/src/routes/datasets/[dataset_id]/[collection_type]/[collection_id]/samples/+page.svelte`
- `lightly_studio_view/src/lib/hooks/useMetadataFilters/useMetadataFilters.ts`
- `lightly_studio_view/src/lib/hooks/useDimensions/useDimensions.ts`
- `lightly_studio_view/src/lib/hooks/useTags/useTags.ts`

- [ ] Remove `untrack(() => collectionId)` / `untrack(() => collection_id)` freezes that bind hooks to initial params.
- [ ] Use one stable top-level hook instance with reactive params (store-backed params pattern) where needed.
- [ ] Verify metadata/dimensions/tags are correct after param-only navigation between collections.
- [ ] Keep the "no hook creation inside reactive runes" rule intact.

## 3) Remove debug instrumentation from production path (P2)

File: `lightly_studio_view/src/routes/datasets/[dataset_id]/[collection_type]/[collection_id]/+layout.svelte`

- [ ] Remove `_rc`, `_log`, and all temporary debug `console.log` calls.
- [ ] Keep idempotency guards that were introduced for loop prevention.

## 4) Apply hook-style cleanup for new Readable support (P2)

Files:

- `lightly_studio_view/src/lib/hooks/useHasEmbeddings/useHasEmbeddings.ts`
- `lightly_studio_view/src/lib/hooks/useAnnotationLabels/useAnnotationLabels.ts`
- `lightly_studio_view/src/lib/hooks/useAnnotationCounts/useAnnotationCounts.ts`
- `lightly_studio_view/src/lib/hooks/useVideoAnnotationsCount/useVideoAnnotationsCount.ts`
- `lightly_studio_view/src/lib/hooks/useVideoFrameAnnotationsCount/useVideoFrameAnnotationsCount.ts`
- `lightly_studio_view/src/lib/hooks/useImagesInfinite/useImagesInfinite.ts`

- [ ] Extract duplicated `isReadable` guard to a shared utility (or align on one local helper pattern).
- [ ] Replace `any` with `unknown` in runtime type guards.
- [ ] Keep public hook APIs backward compatible.

## 5) Validation

- [ ] Run `npm run check` in `lightly_studio_view`.
