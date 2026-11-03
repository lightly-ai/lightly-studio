# Filters only filter: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move every edit out of the filter panel. Selection edits go to the selection pill
(Tag, Annotate). Source management goes to a Settings > Annotation sources tab. Classes nest
under their source in the filter panel, where a tick is an exact (source, class) pair.

**Architecture:** Three slices on the prototype branch. Slice 1 adds two popovers to
`SelectionPill` and four small endpoints, and removes the two edit-mode panels. Slice 2 copies
Michal's Annotation classes tab for sources and strips edit controls from the filter panel.
Slice 3 adds a pair filter and per-source counts to the backend and a source tree component that
replaces `AnnotationCollectionsMenu` and `LabelsMenu`.

**Tech Stack:** FastAPI + SQLModel (DuckDB, Postgres), SvelteKit + Svelte 5, TanStack Query,
hey-api generated client, vitest, pytest.

**Spec:** `.experimental/superpowers/specs/2026-11-03-filters-edit-split-design.md`

## Global Constraints

- Branch `claude/ux-gap-prototype-d56092`. No push, no PR, no CHANGELOG.md edits.
- No database schema change: no new table, no new column, no migration.
- Shell setup for uv and make: `export PATH="/tmp/uv0136/bin:/opt/homebrew/bin:$PATH"`. Main pins
  uv 0.13.6. If `/tmp/uv0136` is gone, recreate it:
  `uv pip install --target /tmp/uv0136 uv==0.13.6`, run from `/tmp`.
- Use absolute paths for file writes; sibling worktrees exist under `.claude/worktrees`.
- Load the skills `AGENTS.md` maps to each path you edit: `python-guide` and `backend-guide` for
  `lightly_studio/src`, `frontend-guide` for `lightly_studio_view`, `best-practices` for new
  modules and components, `glossary` for every user-facing string.
- After a backend API change:
  `cd lightly_studio && rm -f .schema-cache && make export-schema && make mock-webapp-dist`,
  then `cd ../lightly_studio_view && npm run generate-api-client`. The `.schema-cache` file can
  record a failed export as up to date, so delete it first.
- Validation before each commit:
  backend `make static-checks` plus the touched tests with `uv run pytest`; frontend
  `make static-checks` plus `npx vitest run <touched tests>`. Known noise: mypy and test
  collection errors for `adlfs`, `gcsfs`, `s3fs`, `fal_client`;
  `test_server_static_webapp`; `test__get_available_port__preferred_port_in_use`.
- Every commit that changes a user-visible feature updates
  `.experimental/ux-gap-prototype/FEATURES.md` (and `RERUN.md` where a check changes) in the
  same commit.
- Commit messages: imperative subject under 70 chars, a 1 to 3 line body, ending with
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- User-facing terms: "annotation source", "annotation class", "tag", "classification".
  Popover copy from the spec: "Create 'name'", "Added 'a' to 9 items", "Removed 'b' from 3
  items", "All N selected", "Relabel all to…", "Move to annotation source…",
  "Delete raccoon from 1 image in ground_truth?", "Changes to annotation sources save
  immediately."
- Tag and Annotate appear only in edit mode (`isEditingMode` from `useGlobalStorage`).

## Review Focus

1. A select-all that the user then partly unticks must act on the remaining IDs, not on the
   select-all filter. Task 1 pins it.
2. After +, × or create in a popover, the "k/N" counts and the grid tile chips refresh without a
   reload. Tasks 4 and 5 pin it.
3. Renaming in Settings the source that is the pencil target (stored by name in
   `useAnnotationTarget`) keeps it the target under the new name. Task 10 pins it.
4. Deleting a source that has ticked pairs in the tree drops those pairs, so the grid does not
   filter to nothing. Task 14 pins it.
5. T and L do nothing while a text field has focus or the sample details view is open, where
   other tools own the keyboard. Task 8 pins it.

---

## Slice 1: selection pill

### Task 1: Selection target helper

Extract the "filter for an unmodified select-all, else the ID list" rule from `TagsMenu` so every
pill action shares it.

**Files:**
- Create: `lightly_studio_view/src/lib/hooks/useSelectionTarget/useSelectionTarget.ts`
- Test: `lightly_studio_view/src/lib/hooks/useSelectionTarget/useSelectionTarget.test.ts`
- Modify: `lightly_studio_view/src/lib/components/TagsMenu/TagsMenu.svelte` (the
  `assignSelectionToTag` function uses the helper)

**Interfaces:**
- Produces:
  ```ts
  export type SelectionTarget =
      | { kind: 'filter'; filter: GridFilter; size: number }
      | { kind: 'ids'; ids: string[] };
  export function getSelectionTarget(collectionId: string, gridType: GridType): SelectionTarget;
  ```
  It reads `getSelectedSampleIds`, `selectedSampleAnnotationCropIds`, `getSelectAllSnapshot` and
  `getSelectAllAnnotationSnapshot` from `useGlobalStorage`.

- [ ] **Step 1: Write the failing tests**
  - `returns the select-all filter when the selection is unchanged`: snapshot of size 3 and 3
    selected IDs → `{ kind: 'filter', filter: snapshot.filter, size: 3 }`.
  - `returns the IDs after the user unticks items from a select-all`: snapshot size 3, 2 selected
    → `{ kind: 'ids', ids: [the 2 IDs] }`.
  - `uses annotation crop IDs on the annotations grid`: `gridType: 'annotations'` reads
    `selectedSampleAnnotationCropIds` and the annotation snapshot.
- [ ] **Step 2: Run** `npx vitest run src/lib/hooks/useSelectionTarget`. Expected: FAIL, module
  not found.
- [ ] **Step 3: Implement `getSelectionTarget`, then rewrite `assignSelectionToTag` on top of it.**
- [ ] **Step 4: Run** the new tests and `npx vitest run src/lib/components/TagsMenu`. Expected:
  PASS.
- [ ] **Step 5: Commit** "Share the select-all-or-IDs rule for selection actions".

### Task 2: Tag counts for a selection and remove by filter

**Files:**
- Create: `lightly_studio/src/lightly_studio/resolvers/tag_resolver/count_samples_per_tag.py`
- Create: `lightly_studio/src/lightly_studio/resolvers/tag_resolver/remove_samples_from_tag_from_query.py`
- Modify: `lightly_studio/src/lightly_studio/resolvers/tag_resolver/__init__.py`
- Modify: `lightly_studio/src/lightly_studio/api/routes/api/collection_tag.py`
- Test: `lightly_studio/tests/resolvers/tag_resolver/test_count_samples_per_tag.py`,
  `lightly_studio/tests/resolvers/tag_resolver/test_remove_samples_from_tag_from_query.py`,
  `lightly_studio/tests/api/routes/api/test_collection_tag.py`

**Interfaces:**
- Produces:
  ```python
  def count_samples_per_tag(
      session: Session, collection_id: UUID, sample_ids_query: SelectOfScalar[UUID]
  ) -> dict[UUID, int]: ...
  def remove_samples_from_tag_from_query(
      session: Session, tag_id: UUID, sample_ids_query: SelectOfScalar[UUID]
  ) -> None: ...
  ```
  ```text
  POST   /collections/{collection_id}/tags/counts
         body TagCountsBody {sample_ids: list[UUID] | None, filter: GridFilter | None}
         → list[TagCountView {tag_id: UUID, count: int}]   (tags with count 0 are omitted)
  DELETE /collections/{collection_id}/tags/{tag_id}/remove/samples_by_filter
         body TagByFilterBody (existing) → bool
  ```
  Build `sample_ids_query` the same way `add_samples_to_tag_by_filter` does
  (`build_sample_ids_query`). For `sample_ids`, select from `SampleTable` where the ID is in the
  list. Sending neither field is a 422.

- [ ] **Step 1: Write the failing tests**
  - `test_count_samples_per_tag`: 3 samples; tag "a" on 3, tag "b" on 1, tag "c" on none → `{a: 3, b: 1}`.
  - `test_count_samples_per_tag__only_counts_query_samples`: a query over 2 of the 3 → `{a: 2, b: 1}` or `{a: 2}`, depending on where "b" sits.
  - `test_remove_samples_from_tag_from_query`: removes only the samples the query returns; others keep the tag.
  - API: `test_tag_counts__by_ids`, `test_tag_counts__by_filter`, `test_tag_counts__no_target_is_422`, `test_remove_samples_by_filter`, `test_remove_samples_by_filter__tag_in_other_collection_is_404`.
- [ ] **Step 2: Run** `uv run pytest tests/resolvers/tag_resolver tests/api/routes/api/test_collection_tag.py -k "counts or remove"`. Expected: FAIL.
- [ ] **Step 3: Implement both resolvers and routes.** Remove is a batched delete on `SampleTagLinkTable`, like `remove_sample_ids_from_tag_id`.
- [ ] **Step 4: Run** the same command. Expected: PASS. Regenerate the API client.
- [ ] **Step 5: Commit** "Count tags in a selection and remove a tag by filter".

### Task 3: Classification delete for images and class counts for annotations

**Files:**
- Create: `lightly_studio/src/lightly_studio/api/routes/api/annotations/selection_annotations.py`
  (both routes; register the router where `bulk_delete_annotations` is registered)
- Test: `lightly_studio/tests/api/routes/api/annotations/test_selection_annotations.py`

**Interfaces:**
- Produces:
  ```text
  POST /collections/{collection_id}/annotations/classifications/delete_for_samples
       body {sample_ids: list[UUID] | None, filter: GridFilter | None,
             annotation_label_id: UUID, annotation_collection_id: UUID}
       → BulkDeleteAnnotationsResult {deleted_count: int}
  POST /collections/{collection_id}/annotations/label_counts
       body {filter: AnnotationsFilter}
       → list[AnnotationLabelCountView {annotation_label_id: UUID, label_name: str, count: int}]
  ```
  The delete selects classification annotations whose `parent_sample_id` is in the selection,
  with that label and source, and deletes them through the shared `_delete_annotations` in
  `bulk_delete_annotations.py`, so evaluation runs go stale as in the bulk delete. The counts run
  `AnnotationsFilter.apply` and group by label. For an ID selection the frontend sends
  `AnnotationsFilter.sample_ids`, which holds annotation IDs.

- [ ] **Step 1: Write the failing tests**
  - `test_delete_for_samples__only_selected_images_class_and_source`: images A, B, C; "raccoon" classifications in ground_truth on A and B, and in model_v1 on A. Selecting A and C deletes only A's ground_truth raccoon. `deleted_count == 1`.
  - `test_delete_for_samples__by_filter`.
  - `test_delete_for_samples__marks_evaluation_runs_stale`: mirror the existing bulk delete test.
  - `test_label_counts__by_annotation_ids`: 3 deer and 1 fox selected → `[deer 3, fox 1]`.
- [ ] **Step 2: Run** `uv run pytest tests/api/routes/api/annotations/test_selection_annotations.py`. Expected: FAIL.
- [ ] **Step 3: Implement both routes.**
- [ ] **Step 4: Run.** Expected: PASS. Regenerate the API client.
- [ ] **Step 5: Commit** "Delete classifications of a selection and count its classes".

### Task 4: Tag popover

**Files:**
- Create: `lightly_studio_view/src/lib/components/SelectionPill/TagPopover/TagPopover.svelte`
- Create: `lightly_studio_view/src/lib/components/SelectionPill/TagPopover/tagPopover.helpers.ts`
- Create: `lightly_studio_view/src/lib/hooks/useSelectionTagCounts/useSelectionTagCounts.ts`
- Test: `TagPopover.test.ts`, `tagPopover.helpers.test.ts`, `useSelectionTagCounts.test.ts` next to each file

**Interfaces:**
- Consumes: `getSelectionTarget` (Task 1), the generated clients for `tags/counts` and
  `remove/samples_by_filter` (Task 2), existing `createTag`, `addSampleIdsToTagId`,
  `addSamplesToTagByFilter`, `removeThingIdsToTagId`, `useTags`.
- Produces:
  ```ts
  // TagPopover props
  { collectionId: string; gridType: GridType; selectedCount: number; open: boolean;
    onOpenChange: (open: boolean) => void }
  export function tagRowActions(count: number, total: number): { canAdd: boolean; canRemove: boolean };
  export function useSelectionTagCounts(collectionId: string, target: SelectionTarget):
      Readable<Map<string, number>>;
  ```
  Use the existing shadcn `Popover` and `Command` components, as `AnnotationSourcePicker` does.
  After each mutation, invalidate the tag count query, the tags query and the grid query
  (Review Focus 2).

- [ ] **Step 1: Write the failing tests**
  - helpers: `tagRowActions(0, 3)` gives `{canAdd: true, canRemove: false}`, `(1, 3)` gives both, and `(3, 3)` gives `{canAdd: false, canRemove: true}`.
  - popover: rows show "k/N" from the counts; clicking + calls add (by filter when the target is a filter); × calls remove; typing an unknown name shows "Create 'name'" and Enter creates then assigns; after an action the counts query is invalidated; the list container has a max height that fits 5 rows and scrolls.
  - toasts: "Added 'a' to 9 items", "Removed 'b' from 3 items".
- [ ] **Step 2: Run** `npx vitest run src/lib/components/SelectionPill/TagPopover src/lib/hooks/useSelectionTagCounts`. Expected: FAIL.
- [ ] **Step 3: Implement the helpers, the hook and the component.**
- [ ] **Step 4: Run.** Expected: PASS.
- [ ] **Step 5: Commit** "Add the tag popover for the selection pill".

### Task 5: Annotate popover on the Images grid

**Files:**
- Create: `lightly_studio_view/src/lib/components/SelectionPill/ImagesAnnotatePopover/ImagesAnnotatePopover.svelte`
- Test: `ImagesAnnotatePopover.test.ts` next to it

**Interfaces:**
- Consumes: `getSelectionTarget`; `useImageAnnotationCounts` with body
  `{ filter, annotation_type: 'classification', count_mode: 'samples' }`, where the filter is the
  selection (`sample_filter.sample_ids` for IDs, the snapshot filter otherwise) restricted to the
  picked source through `annotations_filter.collection_ids`; `useBulkCreateClassifications`
  (IDs and by-filter); the `delete_for_samples` client (Task 3); `AnnotationSourcePicker` and the
  target rules from `useAnnotationTarget`; `useAnnotationLabels`.
- Produces: props `{ collectionId: string; selectedCount: number; open: boolean; onOpenChange }`.

- [ ] **Step 1: Write the failing tests**
  - `has no source picked when there are several sources`, and + is refused with the existing "pick a source" toast.
  - `cannot pick a hidden source`: matches the pencil picker rule.
  - rows show "k/N"; + calls bulk create with `class_name` and `annotation_collection_name`; a new name shows "Create 'name'".
  - × opens the confirm "Delete raccoon from 1 image in ground_truth?"; Cancel calls nothing; Delete calls `delete_for_samples` with the label and source IDs.
  - after an action, counts and grid queries are invalidated.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run.** Expected: PASS.
- [ ] **Step 5: Commit** "Add the classification popover for selected images".

### Task 6: Annotate popover on the Annotations grid

**Files:**
- Create: `lightly_studio_view/src/lib/components/SelectionPill/AnnotationsAnnotatePopover/AnnotationsAnnotatePopover.svelte`
- Test: `AnnotationsAnnotatePopover.test.ts` next to it

**Interfaces:**
- Consumes: `getSelectionTarget`; the `label_counts` client (Task 3); `useBulkRelabelAnnotations`
  (from main); `useBulkDeleteAnnotations` with `DeleteAnnotationsDialog`;
  `useMoveAnnotationsToSource` with `AnnotationSourcePicker`.
- Produces: the same props as Task 5.

- [ ] **Step 1: Write the failing tests**
  - header reads "All 4 selected"; rows "deer 3" and "fox 1" come from `label_counts`.
  - trash on "fox" opens the delete dialog with count 1; confirming deletes by filter (the selection filter plus `annotation_label_ids: [fox]`).
  - "Relabel all to…" with "raccoon" calls bulk relabel for the whole selection; an unknown name relabels to a new class.
  - "Move to annotation source…" opens the picker; picking calls `useMoveAnnotationsToSource` with the selection.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run.** Expected: PASS.
- [ ] **Step 5: Commit** "Add the annotation popover for selected annotations".

### Task 7: Wire the pill and remove the old panels

**Files:**
- Modify: `lightly_studio_view/src/lib/components/SelectionPill/SelectionPill.svelte` (new props
  `collectionId: string`, `gridType: GridType`, `isEditing: boolean`)
- Modify: the collection `+layout.svelte` (the `SelectionPill` mount passes the new props)
- Delete: `lightly_studio_view/src/lib/components/AnnotationsGrid/SelectedAnnotations/` and its mount in `AnnotationsGrid.svelte`
- Delete: `lightly_studio_view/src/lib/components/BulkClassificationPanel/` and its mount in `Images.svelte`
- Modify: `lightly_studio_view/src/lib/components/TagsMenu/TagsMenu.svelte` (drop `TagAssignInput` and `allowAssign`; delete `TagAssignInput.svelte` and its test)
- Modify: `.experimental/ux-gap-prototype/FEATURES.md`, `RERUN.md` (rows 22 and 23 checks that name the old panels)
- Test: `SelectionPill.test.ts`

- [ ] **Step 1: Write the failing tests**
  - `shows Tag and Annotate in edit mode`; `shows only the count and clear outside edit mode`.
  - Annotate opens `ImagesAnnotatePopover` on the images grid and `AnnotationsAnnotatePopover` on the annotations grid.
- [ ] **Step 2: Run** `npx vitest run src/lib/components/SelectionPill`. Expected: FAIL.
- [ ] **Step 3: Implement; delete the old panels and their tests.** Grep for leftover imports.
- [ ] **Step 4: Run** frontend `make static-checks` and the full `npx vitest run`. Expected: 0 errors, all pass.
- [ ] **Step 5: Commit** "Move selection edits into the selection pill".

### Task 8: T and L shortcuts

**Files:**
- Create: `lightly_studio_view/src/lib/hooks/usePillShortcuts/usePillShortcuts.ts`
- Modify: `SelectionPill.svelte` (the window keydown listener)
- Modify: `lightly_studio_view/src/lib/components/Settings/settingsDialogState.svelte.ts`,
  `ShortcutsTab`, `SettingsDialog.svelte` (two rows, saved with "Save changes")
- Test: `usePillShortcuts.test.ts`, `SelectionPill.test.ts`, `SettingsDialog.test.ts`

**Interfaces:**
- Produces:
  ```ts
  export function usePillShortcuts(): {
      tagKey: Readable<string>;      // default 't'
      annotateKey: Readable<string>; // default 'l'
      setKeys: (keys: { tagKey: string; annotateKey: string }) => void;
  };
  ```
  localStorage key `lightly-studio.pill-shortcuts`, stubbed in tests like `useOnboarding`.

- [ ] **Step 1: Write the failing tests**
  - `T opens the tag popover in edit mode with a selection`; `L opens the annotate popover`.
  - `ignores T while an input has focus` (Review Focus 5); `ignores T outside edit mode`; `ignores T with an empty selection`.
  - settings: the Shortcuts tab lists "Open tag menu" and "Open annotate menu"; recording a new key and saving calls `setKeys`; a key already bound elsewhere shows the existing conflict error.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement.** The listener lives in `SelectionPill`, which mounts only on collection grids, so the sample details view never receives these keys.
- [ ] **Step 4: Run.** Expected: PASS.
- [ ] **Step 5: Commit** "Open the pill menus with T and L"; update FEATURES.md in the same commit.

## Slice 2: Settings > Annotation sources

### Task 9: Sources with counts and create

**Files:**
- Modify: `lightly_studio/src/lightly_studio/api/routes/api/annotation.py` (next to `read_annotation_collections`)
- Modify: `lightly_studio/src/lightly_studio/resolvers/collection_resolver/` (one new count function)
- Test: `lightly_studio/tests/api/routes/api/test_annotation.py`

**Interfaces:**
- Produces:
  ```text
  GET  /collections/{collection_id}/annotation_collections_with_counts
       → list[AnnotationCollectionWithCountView {collection_id, name, annotation_types, annotation_count}]
  POST /collections/{collection_id}/annotation_collections   body {name: str}
       → AnnotationCollectionView   (409 when the name exists)
  ```
  POST calls `collection_resolver.get_or_create_child_collection`.

- [ ] **Step 1: Write the failing tests**: counts per source, including 0 for an empty source; create returns the new source; it then appears in `GET annotation_collections`; a duplicate name returns 409.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run.** Expected: PASS. Regenerate the API client.
- [ ] **Step 5: Commit** "List annotation sources with counts and create one".

### Task 10: Annotation sources tab

**Files:**
- Create: `lightly_studio_view/src/lib/components/Settings/AnnotationSourcesTab/` (structure
  mirrors `AnnotationClassesTab`: `AnnotationSourcesTab.svelte`, a row, a list, a search input, a
  delete dialog wrapper, `useAnnotationSources`, an `index.ts`)
- Modify: `SettingsTabs.svelte` (new tab `annotation-sources` after `annotation-classes`)
- Modify: `SettingsDialog.svelte` (footer note on this tab too)
- Test: `AnnotationSourcesTab.test.ts`, mirroring `AnnotationClassesTab.test.ts`

**Interfaces:**
- Consumes: Task 9 endpoints; the prototype's `useRenameAnnotationSource`,
  `useDeleteAnnotationSource` and `DeleteAnnotationSource` dialog; `useColorPicker` and
  `useCustomLabelColors`; `useAnnotationTarget`.

- [ ] **Step 1: Write the failing tests**
  - find or add: typing "model" while "model_v1" exists filters to it and Enter adds nothing; "review_round_2" plus Enter calls create and highlights the new row.
  - rename inline; a duplicate name shows an error; rename moves the custom color to the new name.
  - `renaming the pencil target keeps it the target` (Review Focus 3).
  - delete shows the annotation count and the stale-evaluation warning; confirm calls delete.
  - the footer reads "Changes to annotation sources save immediately."
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run.** Expected: PASS.
- [ ] **Step 5: Commit** "Add the Annotation sources tab to Settings"; update FEATURES.md.

### Task 11: Strip edits from the filter panel

**Files:**
- Modify: `lightly_studio_view/src/lib/components/AnnotationCollectionsMenu/AnnotationCollectionsMenu.svelte` (remove the "…" menu and `enableColorPicker`)
- Modify: `lightly_studio_view/src/lib/components/LabelsMenu/LabelsMenu.svelte` and `AnnotationColorLegend` usage (remove the class color picker; keep `LabelVisibilityToggle`)
- Modify: `lightly_studio_view/src/lib/hooks/useSettingsDialog/useSettingsDialog.ts` (`openSettingsDialog(tab?: string)`) and `SettingsDialog.svelte` (open on that tab instead of always `shortcuts`)
- Modify: the annotations section header (gear button, `aria-label="Manage annotation sources"`)
- Modify: FEATURES.md and RERUN.md (rename and delete checks now go through Settings)
- Test: the existing menu tests, `SettingsDialog.test.ts`

- [ ] **Step 1: Write the failing tests**: no "…" and no color picker on source rows; no color picker on class rows; the eye toggles remain; the gear opens Settings on Annotation sources; `openSettingsDialog()` with no argument still opens Shortcuts.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement.** Remove tests that covered the moved controls.
- [ ] **Step 4: Run** frontend `make static-checks` and the full vitest. Expected: 0 errors, all pass.
- [ ] **Step 5: Commit** "Keep only filters in the filter panel".

## Slice 3: nested source and class filter

### Task 12: Pair filter

**Files:**
- Modify: `lightly_studio/src/lightly_studio/resolvers/annotations/annotations_filter.py`
- Test: `lightly_studio/tests/resolvers/annotations/test_annotations_filter.py`

**Interfaces:**
- Produces:
  ```python
  class SourceLabelPair(BaseModel):
      collection_id: UUID
      annotation_label_id: UUID

  # AnnotationsFilter
  source_label_pairs: list[SourceLabelPair] | None = None
  ```
  In `_apply_predicates`: `or_(*(and_(collection_id == p.collection_id, label_id == p.annotation_label_id) for p in pairs))`
  on the same annotation row. `include_unannotated_samples` keeps its OR with the parent query.

- [ ] **Step 1: Write the failing tests**
  - `test_pairs__one_pair`: deer in ground_truth matches only images with a ground_truth deer.
  - `test_pairs__two_pairs_or`: deer in ground_truth, or raccoon in model_v1.
  - `test_pairs__mismatched_pair_excluded`: an image with only a raccoon in ground_truth does not match the two pairs above.
  - `test_pairs__with_unannotated_samples`.
  - Both `apply` (annotations grid) and `apply_to_parent_sample_query` (images grid).
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the test plus `tests/resolvers/annotations`. Expected: PASS. Regenerate the API client.
- [ ] **Step 5: Commit** "Filter annotations by exact source and class pairs".

### Task 13: Per-source counts

**Files:**
- Create: `lightly_studio/src/lightly_studio/resolvers/image_resolver/count_image_annotations_by_source.py`
- Modify: `lightly_studio/src/lightly_studio/api/routes/api/image/routes.py`
- Test: `lightly_studio/tests/resolvers/image_resolver/test_count_image_annotations_by_source.py`

**Interfaces:**
- Produces:
  ```python
  def count_image_annotations_by_source(
      session: Session, collection_id: UUID, image_filter: ImageFilter | None = None,
      count_mode: AnnotationCountMode = AnnotationCountMode.SAMPLES,
  ) -> list[SourceLabelCount]: ...
  # SourceLabelCount: annotation_collection_id, annotation_label_id, label_name,
  #                   current_count, total_count
  ```
  ```text
  POST /collections/{collection_id}/images/annotations/count_by_source
       body ReadCountImageAnnotationsRequest (existing)
  ```
  Follow `get_total_counts.py` and `get_current_counts.py`, adding the annotation's collection ID
  to the select and the group by. Before computing current counts, drop the request's own
  `source_label_pairs`, the same rule today's class counts apply to their own class filter.

- [ ] **Step 1: Write the failing tests**: deer counted separately per source; current counts follow a tag filter; the request's own pairs do not shrink the counts.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run.** Expected: PASS. Regenerate the API client.
- [ ] **Step 5: Commit** "Count image annotations per source and class".

### Task 14: Pair selection state and requests

**Files:**
- Create: `lightly_studio_view/src/lib/hooks/useAnnotationPairFilter/useAnnotationPairFilter.ts`
- Modify: `lightly_studio_view/src/lib/hooks/useTabFilters/useTabFilters.ts` (keep pairs per tab)
- Modify: `Images.svelte`, `AnnotationsGrid.svelte` and the collection `+layout.svelte` (send
  `source_label_pairs`; stop sending the source scope from `annotationSourceScope.ts` and the
  class IDs from `selectedAnnotationFilterIds` on these two grids)
- Test: `useAnnotationPairFilter.test.ts`

**Interfaces:**
- Produces:
  ```ts
  export function useAnnotationPairFilter(collectionId: string): {
      pairs: Readable<SourceLabelPair[]>;
      togglePair: (sourceId: string, labelId: string) => void;
      setSource: (sourceId: string, labelIds: string[], checked: boolean) => void;
      sourceState: (sourceId: string, labelIds: string[]) => 'checked' | 'partial' | 'unchecked';
      dropSource: (sourceId: string) => void;
      clear: () => void;
  };
  ```

- [ ] **Step 1: Write the failing tests**: toggle and set; the tri-state cases; nothing ticked sends no `source_label_pairs`; pairs survive a switch to the Annotations tab and back; `dropSource` runs when a source disappears from the source list (Review Focus 4); clear-all-filters clears the pairs.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement and wire the requests.**
- [ ] **Step 4: Run** the hook tests and the Images, AnnotationsGrid and layout tests. Expected: PASS.
- [ ] **Step 5: Commit** "Keep the annotation filter as source and class pairs".

### Task 15: Source tree

**Files:**
- Create: `lightly_studio_view/src/lib/components/AnnotationSourceTree/AnnotationSourceTree.svelte`
- Modify: the collection `+layout.svelte` (images and annotations grids render the tree in place
  of `AnnotationCollectionsMenu` and `LabelsMenu`; other grids keep `LabelsMenu`)
- Modify: FEATURES.md and RERUN.md (a new check for pairs)
- Test: `AnnotationSourceTree.test.ts`

**Interfaces:**
- Consumes: `useAnnotationPairFilter`, the `count_by_source` client, `useAnnotationCollections`,
  the visibility hooks behind today's eye toggles, `useCustomLabelColors` for the read-only dots,
  and the pinned "No annotations" row from `LabelsMenu`.
- Produces: props `{ collectionId: string }`.

- [ ] **Step 1: Write the failing tests**
  - two sources: parent rows with chevron, tri-state checkbox, count and eye, plus nested class rows.
  - one source: a flat class list, with no parent row.
  - an empty source renders collapsed, with no children.
  - the class eye under ground_truth also shows hidden under model_v1.
  - "No annotations" stays at the bottom and keeps its behavior.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the full frontend static checks and vitest. Expected: 0 errors, all pass.
- [ ] **Step 5: Commit** "Nest annotation classes under their source in the filters".

### Task 16: Export scope and Copy as code

**Files:**
- Modify: `lightly_studio_view/src/lib/components/ExportSamples/ExportScope/`,
  `ExportAsCode/buildExportCode.ts`
- Test: `buildExportCode.test.ts`, the ExportScope test

- [ ] **Step 1: Write the failing tests**
  - pairs within one source produce the same code as today's class filter.
  - pairs across two sources produce no code. This matches today's "gives no code when only some annotation sources are selected" path and its message.
  - the scope text names the pairs ("deer in ground_truth, raccoon in model_v1").
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run.** Expected: PASS.
- [ ] **Step 5: Commit** "Export the source and class pair filter".

### Task 17: GUI check

- [ ] **Step 1:** Run `.experimental/ux-gap-prototype/run_caltech.sh prototype 8001` with `--reload` on `~/data/caltech-ux-run-dbs/prototype.db`.
- [ ] **Step 2:** Walk the new RERUN.md checks for the pill, Settings and the tree. Take a screenshot per slice.
- [ ] **Step 3:** Run the full backend suite (`uv run pytest -n 8`) and the full vitest. Record the results in the side-session ledger.
