# ENT-570: 3D Annotation Source Picker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** In the 3D point cloud workspace, the labeler picks which annotation source new cuboids go to: in the right panel, in the create modal when the source is unknown, and sees the target in the viewport.

**Architecture:** A pure resolver and a small hook inside `PointCloudLabelingWorkspace/useCuboidTargetSource/` own the 3D target-source state; the workspace controller creates it once. The panel, the create flow, the class modal (through a generic slot in the shared `SelectClassDialog`) and a viewport chip read it. No backend change. No imports from the 2D `hooks/useAnnotationTarget` or the 2D `AnnotationLabelContext`.

**Tech Stack:** SvelteKit 5 (runes), TypeScript, TanStack Query, Vitest + Testing Library, Tailwind/shadcn UI.

**Spec:** `.experimental/superpowers/specs/2026-11-17-ent-570-3d-annotation-source-picker-design.md`

## Global Constraints

- Load `frontend-guide`, `clean-code` and `glossary` skills before editing `.ts`/`.svelte`; `changelog` before editing `CHANGELOG.md`.
- 3D code must not import from `$lib/hooks/useAnnotationTarget` or `$lib/contexts/SampleDetailsAnnotation.svelte`.
- Shared components get only optional, generic props; every 2D call site keeps working unchanged.
- User-facing term: "annotation source". Exact strings:
  - `Pick where new annotations go.`
  - `Loading annotation sources…`
  - `Could not load the annotation sources. Reload the page to add annotations.`
  - Success toast: `Cuboid added to {source}` (replaces `Annotation created successfully` for cuboids)
  - Chip: `New cuboids go to {source}`
  - Empty group: `No cuboids on this tick`
- Default source name when none exist: `annotation`.
- Pick storage: `useGlobalStorage().lastAnnotationSource`, keyed by `annotationSourceCollectionId`.
- Picking a source is only possible for role `labeler` or higher and in editing mode (same gate as 2D: `hasMinimumRole(user?.role, 'labeler') && isEditingMode`).
- Each task is one commit. Validate per task: `cd lightly_studio_view && npx vitest run <changed test files>`; before the last commit also `make static-checks`.

## Review Focus

- A source renamed or deleted in another tab while it is the pick: the next cuboid must ask, never re-create the old name. (Task 1 + Task 2 tests)
- Switching sequence/collection while a name was typed but not yet created: the typed name must not leak into the other collection. (Task 2 test)
- Cancelling the create modal: nothing is created and the pick is unchanged. (Task 6 test)
- Typing an existing source name in "New source…": selects that source, does not mark it as new. (Task 4 test)
- Keyboard confirm (Enter) in the class modal while no source is chosen: must not confirm. (Task 5 test)

---

### Task 1: Pure target-source rules

**Files:**
- Create: `lightly_studio_view/src/lib/components/PointCloudLabelingWorkspace/useCuboidTargetSource/resolveCuboidTargetSource.ts`
- Test: `.../useCuboidTargetSource/resolveCuboidTargetSource.test.ts`

**Interfaces:**
- Produces:
  ```ts
  export const DEFAULT_CUBOID_SOURCE_NAME = 'annotation';
  export const CUBOID_SOURCE_MESSAGES: { pick: string; loading: string; error: string };
  export interface CuboidTarget {
      /** Where the next cuboid goes; null while unknown. */
      targetSource: string | null;
      /** Why creation must stop with a toast (loading, load error). Null otherwise. */
      blockedReason: string | null;
      /** Several sources and no valid pick: the create modal must ask. */
      needsPick: boolean;
  }
  export function resolveCuboidTargetSource(params: {
      pick: string | undefined;
      typedSource: string | null;
      sourceNames: string[] | undefined; // undefined while loading
      isError: boolean;
  }): CuboidTarget;
  export function isCuboidPickRemoved(params: {
      pick: string; previousNames: string[]; nextNames: string[];
  }): boolean;
  ```

- [ ] **Step 1: Write the failing tests** — one `it` per rule, asserting the full `CuboidTarget`:
  - pick in names → `{ targetSource: pick, blockedReason: null, needsPick: false }`
  - pick not in names, several names → `{ null, null, needsPick: true }`
  - `typedSource === pick`, not in names → typed name, no block
  - one name, no pick → that name; no names → `'annotation'`
  - several names, no pick → `needsPick: true`
  - `sourceNames: undefined` → `blockedReason: CUBOID_SOURCE_MESSAGES.loading`, also with a pick
  - `isError: true` (with or without names) → `blockedReason: CUBOID_SOURCE_MESSAGES.error`
  - `isCuboidPickRemoved`: true when the pick left the list (incl. rename: one name gone, one new); false when still listed; false for a typed name never listed.
- [ ] **Step 2: Run** `npx vitest run src/lib/components/PointCloudLabelingWorkspace/useCuboidTargetSource` → FAIL (module missing).
- [ ] **Step 3: Implement** both functions. Error check comes first, then loading. Copy the three message strings verbatim from Global Constraints (do not import from 2D).
- [ ] **Step 4: Run** the same command → PASS.
- [ ] **Step 5: Commit** `feat(3d): add rules for the annotation source of new cuboids`

---

### Task 2: Target-source hook, wired into the workspace controller

**Files:**
- Create: `.../useCuboidTargetSource/useCuboidTargetSource.svelte.ts`, `.../useCuboidTargetSource/index.ts`
- Modify: `.../useWorkspaceSceneData/useWorkspaceSceneData.svelte.ts` (expose load state)
- Modify: `.../createWorkspaceController.svelte.ts` (create and return `targetSource`)
- Test: `.../useCuboidTargetSource/useCuboidTargetSource.svelte.test.ts`, extend `useWorkspaceSceneData.svelte.test.ts`

**Interfaces:**
- Consumes: Task 1.
- Produces:
  ```ts
  // useWorkspaceSceneData return value gains:
  readonly annotationSourceNames: string[] | undefined; // undefined until loaded
  readonly annotationSourcesError: boolean;
  refetchAnnotationSources(): Promise<unknown>;

  export interface CuboidTargetSourceState extends CuboidTarget {
      /** A name typed on this page whose source is not created yet. */
      readonly typedSource: string | null;
      setTarget(name: string, options?: { isNew?: boolean }): void;
  }
  export function useCuboidTargetSource(params: {
      getCollectionId: () => string | undefined;
      getSourceNames: () => string[] | undefined;
      getIsError: () => boolean;
  }): CuboidTargetSourceState;

  // createWorkspaceController return value gains:
  targetSource: CuboidTargetSourceState;
  ```

- [ ] **Step 1: Write the failing tests** (use `$effect.root` + `flushSync`, as in `usePointCloudTickNavigation.svelte.test.ts`; mock `useGlobalStorage` with a real `writable` for `lastAnnotationSource`):
  - `setTarget('labels')` stores `{ [collectionId]: 'labels' }` and `targetSource` becomes `labels`.
  - `setTarget('review', { isNew: true })` with names `['a','b']` → `targetSource: 'review'`, `typedSource: 'review'`.
  - `setTarget('  ')` changes nothing.
  - Pick `labels`, names change `['labels','preds']` → `['labels_v2','preds']` → pick removed from storage, `needsPick: true`.
  - Typed name in collection A, collection changes to B → `typedSource` is null.
  - Scene data: `annotationSourceNames` is `undefined` before the query resolves and the names after; `annotationSourcesError` mirrors `isError`.
- [ ] **Step 2: Run** the two test files → FAIL.
- [ ] **Step 3: Implement.** Pick read via `fromStore(lastAnnotationSource)`; write via `updateLastAnnotationSource` / `removeLastAnnotationSource`. `typedSource` is `$state<{ collectionId; name } | null>` and only counts for the current collection. Forget a removed pick with an `$effect` + `untrack` comparing previous and next names of the same collection (same idea as 2D, own code). In the controller create `targetSource` before `editing` and return it.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat(3d): track the annotation source for new cuboids per collection`

---

### Task 3: Move the source radio and "New source" input to a shared place

Pure move so 2D and 3D share the two presentational atoms without 3D importing from `SampleDetails/`.

**Files:**
- Move: `lib/components/SampleDetails/AnnotationTargetRadio/` → `lib/components/AnnotationSource/AnnotationTargetRadio/`
- Move: `lib/components/SampleDetails/NewAnnotationSourceInput/` → `lib/components/AnnotationSource/NewAnnotationSourceInput/`
- Modify: their 2D importers (`AnnotationSourceGroupList.svelte`, `SampleDetailsAnnotationSegment.svelte`) and moved tests.
- Modify: `AnnotationTargetRadio.svelte`: `isSourceHidden` becomes optional, default `false`.

- [ ] **Step 1:** `git mv` both folders; update imports.
- [ ] **Step 2: Run** `npx vitest run src/lib/components/AnnotationSource src/lib/components/SampleDetails` → PASS, no behaviour change.
- [ ] **Step 3: Commit** `refactor: move the annotation source radio and input out of SampleDetails`

---

### Task 4: Pick the source in the right panel

**Files:**
- Modify: `.../CuboidLayer/PointCloudAnnotationList/pointCloudAnnotationList.ts` (`groupAnnotationsBySource`)
- Modify: `.../PointCloudAnnotationList/PointCloudAnnotationListGroup/PointCloudAnnotationListGroup.svelte`
- Modify: `.../PointCloudAnnotationList/PointCloudAnnotationList.svelte`, `.../PointCloudRightSidePanel/PointCloudRightSidePanel.svelte`, `.../WorkspacePanels/WorkspacePanels.svelte`
- Test: `pointCloudAnnotationList.test.ts`, `pointCloudRightSidePanel.test.ts`, stories updated (`PointCloudAnnotationList.stories.svelte`: add "Pick a source" and "Empty source" stories)

**Interfaces:**
- Consumes: Task 2 `controller.targetSource`, Task 3 `AnnotationTargetRadio`, `NewAnnotationSourceInput`.
- Produces (new optional props, passed through panel → list):
  ```ts
  targetSourceName?: string | null;
  pendingSourceName?: string | null;   // typedSource, shown as an empty group
  needsPick?: boolean;
  onPickSource?: (name: string, options?: { isNew?: boolean }) => void; // absent = no radios
  ```
  `PointCloudAnnotationListGroup` gains `isTarget?: boolean`, `needsPick?: boolean`, `onPick?: () => void`.

- [ ] **Step 1: Write the failing tests:**
  - `groupAnnotationsBySource` returns a group with `cuboids: []` for a source without cuboids (update the old "skips empty sources" test); unknown-source fallback unchanged.
  - Panel with `onPickSource`: one radio per source, `aria-checked` on `targetSourceName`; clicking `preds` calls `onPickSource('preds')`.
  - `needsPick: true` → text `Pick where new annotations go.` is shown; false → not shown.
  - Empty source group shows `No cuboids on this tick`.
  - "New source…" with `review` → `onPickSource('review', { isNew: true })`; with existing `labels` → `onPickSource('labels')`.
  - `pendingSourceName: 'review'` renders a `review` group checked as target.
  - Without `onPickSource`: no radios, no "New source…".
- [ ] **Step 2: Run** the list and panel tests → FAIL.
- [ ] **Step 3: Implement.** Radio sits outside `CollapsibleTrigger` (no nested buttons). In `WorkspacePanels.svelte` pass `onPickSource` only when `hasMinimumRole(user?.role, 'labeler') && presentation.isEditingMode`, plus `targetSourceName`, `pendingSourceName`, `needsPick` from `controller.targetSource`.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat(3d): pick the annotation source for new cuboids in the right panel`

---

### Task 5: Send the source when creating a cuboid

**Files:**
- Modify: `.../useCreateCuboidAnnotation/useCreateCuboidAnnotation.svelte.ts`
- Modify: `.../useWorkspaceEditing/useWorkspaceEditing.svelte.ts` (new param, refetch sources)
- Modify: `.../createWorkspaceController.svelte.ts` (pass `() => targetSource`)
- Test: `useCreateCuboidAnnotation.svelte.test.ts`, `createWorkspaceController.svelte.test.ts`

**Interfaces:**
- Consumes: Task 2 `CuboidTargetSourceState`, `refetchAnnotationSources`.
- Produces: `useCreateCuboidAnnotation` params gain `getTarget: () => CuboidTarget`; `useWorkspaceEditing(getWorkspace, getOptions, getData, getIsEditingMode, getTarget)`.

- [ ] **Step 1: Write the failing tests:**
  - Target `labels` → `createAnnotation` called with `annotation_collection_name: 'labels'`; `toast.success('Cuboid added to labels')`.
  - `blockedReason` set → `toast.error(blockedReason)`, `requestLabel` and `createAnnotation` not called.
  - `needsPick: true` → `toast.error('Pick where new annotations go.')`, nothing created (temporary; Task 6 replaces it with the modal).
  - Editing: after a create whose target is not in `annotationSourceNames`, `refetchAnnotationSources` is called.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement.** Check the target first in `handleCreateCuboid`, before the class lookup. Read `targetSource` again right before `saveCuboid` (it may change while awaiting).
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat(3d): create cuboids in the picked annotation source`

---

### Task 6: Ask for the source in the create modal

**Files:**
- Modify: `lib/components/SelectClassDialog/SelectClassDialog.svelte` (generic props)
- Create: `.../PointCloudLabelingWorkspace/WorkspaceClassDialog/CuboidSourceSection.svelte`
- Modify: `.../WorkspaceClassDialog/WorkspaceClassDialog.svelte`
- Modify: `.../useCreateCuboidAnnotation/useCreateCuboidAnnotation.svelte.ts` (open modal on `needsPick`; expose remembered class)
- Test: `SelectClassDialog.test.ts`, new `WorkspaceClassDialog.test.ts`, `useCreateCuboidAnnotation.svelte.test.ts`

**Interfaces:**
- Consumes: Task 2 `targetSource`, Task 3 atoms, Task 5 `getTarget`.
- Produces:
  ```ts
  // SelectClassDialog, all optional:
  extra?: Snippet;          // rendered below the class list
  canConfirm?: boolean;     // default true; gates the button AND keyboard confirm
  initialLabel?: string;    // preselected class when the dialog opens
  // useCreateCuboidAnnotation return value gains:
  rememberedLabel: string | null; // last class for the collection
  ```
  `CuboidSourceSection` props: `{ sourceNames: string[]; selected: { name: string; isNew: boolean } | null; onSelect(v: { name: string; isNew: boolean }): void }`.

- [ ] **Step 1: Write the failing tests:**
  - `SelectClassDialog` without new props: existing tests unchanged and green (2D unaffected).
  - `canConfirm={false}`: Confirm disabled; Enter in the list does not call `onConfirm`.
  - `initialLabel="car"`: `car` is selected on open.
  - `WorkspaceClassDialog`: with `needsPick`, no source preselected and Confirm disabled; picking `preds` + class `car` + Confirm → `targetSource.setTarget('preds')` then `handleClassSelected('car')`; with a resolved target it is preselected; typing a new name → `setTarget(name, { isNew: true })`; Cancel → no `setTarget`.
  - `useCreateCuboidAnnotation`: remembered class + `needsPick` → `requestLabel` is called (no toast); after it resolves with the target now `preds`, the cuboid is created in `preds`. Modal cancelled → nothing created.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement.** Open the modal when the class is unknown, `selectClass` is true, or `needsPick`. `WorkspaceClassDialog` keeps the draft source in local `$state`, resets it on open, passes `extra`, `canConfirm={!!draft}` and `initialLabel={editing.rememberedLabel}`, and on confirm calls `setTarget` before `handleClassSelected`. Remove the temporary `needsPick` toast from Task 5.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat(3d): ask for the annotation source when creating a cuboid`

---

### Task 7: Show the target in the viewport, changelog

**Files:**
- Create: `.../CuboidTargetChip/CuboidTargetChip.svelte`, `.../CuboidTargetChip/index.ts`, `.../CuboidTargetChip/CuboidTargetChip.test.ts`
- Modify: `.../WorkspaceViewport/WorkspaceViewport.svelte` (perspective header only)
- Modify: `CHANGELOG.md` (`### Added` under `## [Unreleased]`)

**Interfaces:**
- Consumes: Task 2 `controller.targetSource`; `layout.effectiveTool`.
- Produces: `CuboidTargetChip` props `{ targetSource: string | null; needsPick: boolean; blockedReason: string | null }`.

- [ ] **Step 1: Write the failing tests:** `labels` → text `New cuboids go to labels`; `needsPick` → `Pick where new annotations go.` with warning styling (`data-state="warning"`); `blockedReason` → that text with warning styling.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** the chip; render it in the perspective viewport header only while `layout.effectiveTool === 'create-cuboid'`, with `pointer-events-none`. Changelog entry: "Choose the annotation source for new cuboids in the point cloud workspace, in the Annotations panel or when you create a cuboid."
- [ ] **Step 4: Run** the chip test, then `cd lightly_studio_view && make static-checks && make test` → all green.
- [ ] **Step 5: Commit** `feat(3d): show where new cuboids go while drawing`

---

## Out of scope (follow-up ticket)

"Move/Copy track to source": per-track, needs a backend endpoint. See the spec's Non-goals.
