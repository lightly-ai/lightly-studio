# Query Reactivity Refactor Plan

## Goal

Fix systemic `effect_update_depth_exceeded` issues caused by creating query hooks inside Svelte rune reactive contexts (`$derived`, `$derived.by`, route-driven conditionals), with the first priority on group grid -> image grid navigation.

## Core Rule

Query hooks must be instantiated once per component instance, never inside:

- `$derived(...)`
- `$derived.by(...)`
- conditional branches that re-run with reactive state

Dynamic inputs must flow through stores/derived params passed to an existing query observer.

## Strategy

1. Refactor query hooks to accept reactive params (`Readable<T>`) where needed.
2. Replace conditional hook creation with unconditional creation + `enabled` flags.
3. Separate side-effectful state initialization from query hook instantiation.
4. Migrate highest-risk route/layout first, then sweep all remaining call sites.
5. Add guardrails (lint/check) to prevent reintroducing hook creation in reactive blocks.

## Phase 1: Stabilize Reported Navigation Path

Target files:

- `src/routes/datasets/[dataset_id]/[collection_type]/[collection_id]/+layout.svelte`
- `src/routes/datasets/[dataset_id]/[collection_type]/[collection_id]/samples/+page.svelte`

Tasks:

1. Remove query hook calls from `$derived(...)` and `$derived.by(...)`.
2. Instantiate all route-level queries once at top level.
3. For multi-route logic (annotation counts), create all relevant queries once and switch only which result is consumed.
4. Use query `enabled` conditions to avoid unnecessary network calls.

## Phase 2: Refactor Shared Hooks

Target hooks:

- `src/lib/hooks/useAnnotationCounts/useAnnotationCounts.ts`
- `src/lib/hooks/useVideoAnnotationsCount/useVideoAnnotationsCount.ts`
- `src/lib/hooks/useVideoFrameAnnotationsCount/useVideoFrameAnnotationsCount.ts`
- `src/lib/hooks/useGroupsInfinite/useGroupsInfinite.ts`
- `src/lib/hooks/useFrames/useFrames.ts`
- `src/lib/hooks/useVideos/useVideos.ts`
- `src/lib/hooks/useMetadataFilters/useMetadataFilters.ts`

Tasks:

1. Support store-driven/reactive params without re-creating query instances.
2. Ensure subscriptions are not leaked (`subscribe` cleanup where applicable).
3. Move fetch/initialization side effects out of plain hook calls where possible.
4. Keep return shape stable to minimize caller churn.

## Phase 3: Sweep Remaining Call Sites

High-priority files:

- `src/routes/datasets/[dataset_id]/[collection_type]/[collection_id]/groups/+page.svelte`
- `src/routes/datasets/[dataset_id]/[collection_type]/[collection_id]/frames/+page.svelte`
- `src/routes/datasets/[dataset_id]/[collection_type]/[collection_id]/videos/+page.svelte`
- `src/lib/components/FewShotClassifier/ClassifierSamplesGrid.svelte`
- `src/lib/components/PlotPanel/PlotPanel.svelte`

Tasks:

1. Replace `$derived(useX(...))` with top-level hook instantiation.
2. Replace `return useX(...)` inside `$derived.by` with non-reactive hook setup.
3. Keep reactive logic focused on data selection and rendering only.

## Guardrails

1. Add a lint/check rule that fails on:
   - `$derived(use...`
   - `use...` inside `$derived.by(...)`
2. Add review checklist item: "No query hook creation inside reactive blocks."

## Validation

Functional:

1. Group grid -> image grid loads images without page refresh.
2. No `effect_update_depth_exceeded` in console during repeated navigation.
3. Query behavior remains correct for filters, tag selection, and infinite loading.

Tests:

1. Add a focused e2e regression:
   - navigate to groups
   - navigate back to images
   - assert first image item is visible
   - assert no console error matching `effect_update_depth_exceeded`
2. Run `npm run check`.
3. Run targeted e2e(s) for samples/groups navigation.

## Rollout

1. Merge Phase 1 first to unblock users.
2. Ship Phase 2 and Phase 3 in small PRs by domain (samples/videos/frames/details).
3. Keep guardrails in place before completing rollout.
