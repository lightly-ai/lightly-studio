# Query Reactivity MVP Plan: Image Grid Rendering

## Objective

Quickly validate the hypothesis: removing reactive query hook instantiation fixes group -> images navigation without refresh and removes `effect_update_depth_exceeded`.

## Scope

In scope:

- only group -> image grid path
- only code needed to make image grid load reliably on client navigation

Out of scope:

- full architecture cleanup
- full hook API redesign
- broad lint guardrails
- non-image routes unless required by the image-grid path

## Checklist

## 0) Branch and baseline

- [ ] Create branch `hack/mvp-query-reactivity-image-grid`.
- [ ] Reproduce current bug manually:
  - go to groups
  - navigate to images
  - confirm blank/failed load + console `effect_update_depth_exceeded`
- [ ] Capture baseline evidence in PR description (short gif or console screenshot).

## 1) Stop creating hooks in reactive blocks in layout

File: `lightly_studio_view/src/routes/datasets/[dataset_id]/[collection_type]/[collection_id]/+layout.svelte`

- [x] Replace these with top-level hook calls (no `$derived(use...)`, no `$derived.by(() => use...)`):
  - `useHasEmbeddings`
  - `useAnnotationLabels`
  - `useMetadataFilters`
  - `useDimensions`
- [x] Remove `annotationCounts` hook creation inside `$derived.by`.
- [x] Instantiate all three annotation-count queries once at top level (`useAnnotationCounts`, `useVideoAnnotationCounts`, `useVideoFrameAnnotationCounts`).
- [x] Gate each query with `enabled` so only the active route query fetches.
- [x] Keep only reactive query-result selection in runes; no hook creation in runes.

### Step 1 Learnings (important for next steps)

- Top-level hook creation with reactive inputs in Svelte 5 should use store-backed params (`toStore(() => params)` or equivalent hook support for `Readable` params) to avoid `state_referenced_locally` warnings while keeping a single hook instance.
- For route-dependent query switching, instantiate all candidate queries once and switch fetch behavior with `enabled`; avoid conditionally creating hooks inside runes.
- Keep downstream reactivity focused on query results only (`$query.data` selection in runes), not hook creation.
- The previously observed `page.images` type mismatch in `Samples.svelte` is resolved as part of Step 3.

## 2) Stop creating hooks in reactive blocks in samples page

File: `lightly_studio_view/src/routes/datasets/[dataset_id]/[collection_type]/[collection_id]/samples/+page.svelte`

- [x] Replace `$derived(useTags(...))` with direct top-level `useTags(...)`.
- [x] Keep the existing `clearTagsSelected` behavior unchanged.

### Step 2 Learnings (important for next steps)

- `useTags` currently accepts a plain `collection_id: string`, so removing reactive hook creation required top-level instantiation with a non-reactive value capture (`untrack(() => collection_id)`), not `$derived(useTags(...))`.
- For follow-up cleanup, prefer the Step 1 pattern (`Readable`/`toStore` params) so hooks can react to param changes without re-instantiation; this is especially relevant for Step 3 query stability and Step 4 subscription lifecycle cleanup.
- Keeping `clearTagsSelected` in the existing `$effect` preserved behavior while decoupling it from hook creation timing, which reduces risk of effect-loop coupling.

## 3) Keep image query observer stable

File: `lightly_studio_view/src/lib/components/Samples/Samples.svelte`

- [x] Confirm `useImagesInfinite(filterParams)` is called once (not inside `$derived`/conditional).
- [x] Keep `filterParams` updates idempotent (existing `isEqual` guard stays).

### Step 3 Learnings (important for next steps)

- If an effect both reads and writes the same store-backed params (`filterParams`), read with `untrack(...)` to avoid read->write retrigger loops.
- Prefer passing a `Readable` params store directly to query hooks (`useImagesInfinite(filterParams)`) so one observer instance can react to param changes.
- Keep response-shape usage aligned with generated API types (`ReadImagesResponse.data` for image list) to avoid type drift blocking Step 7 checks.

## 4) Remove metadata subscription churn

File: `lightly_studio_view/src/lib/hooks/useMetadataFilters/useMetadataFilters.ts`

- [x] Prevent repeated unmanaged `createQuery(...).subscribe(...)` calls across route transitions.
- [x] Replace unmanaged subscriptions with a single query store lifecycle and proper cleanup.
- [x] Ensure collection switches do not accumulate subscriptions.

### Step 4 Learnings (important for next steps)

- Query subscription lifecycle needs explicit ownership: keep exactly one active subscription, and always unsubscribe on terminal states (success/error).
- Deduplicate by both loaded and in-flight collection (`lastCollectionId` + active collection tracking) to avoid duplicate observers during rapid route changes.
- Extracting metadata-sync logic into a pure helper reduces churn in the subscribe callback and makes cleanup paths easier to reason about.

## 5) Validate manually first (fast feedback)

- [ ] Navigate groups -> images 10 times.
- [ ] Confirm first `sample-grid-item` appears every time without refresh.
- [ ] Confirm console has no `effect_update_depth_exceeded`.
- [ ] Confirm infinite scroll still loads next pages in images grid.

## 6) Add one targeted regression test

Test file candidate: `lightly_studio_view/e2e/general/samples-grid.e2e-test.ts`

- [ ] Add test: groups -> images navigation renders first sample.
- [ ] Add console error capture in test and assert no message contains `effect_update_depth_exceeded`.

## 7) Sanity checks

- [x] Run `npm run check`.
- [ ] Run only targeted e2e spec(s) for this scenario.
- [ ] Document scope limits and follow-up work in PR notes.

## Go/No-Go

Go:

- [ ] Bug no longer reproducible on group -> images navigation.
- [ ] No `effect_update_depth_exceeded` during repeated navigation.
- [ ] Image grid renders and paginates.

No-Go:

- [ ] Loop still occurs, or image grid still fails after navigation.
- [ ] In that case, add targeted logging around remaining query creators and run one narrowing pass before broader refactor.
