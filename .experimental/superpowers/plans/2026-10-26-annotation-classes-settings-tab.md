# Annotation Classes Settings Tab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an "Annotation classes" settings tab to add, find, rename, recolor, and delete the annotation classes of the current dataset, with an annotation count per class.

**Architecture:** Backend: a new list-with-counts endpoint, and the class delete endpoint also deletes the class's annotations through logic shared with the bulk annotation delete (which marks evaluation runs stale). Frontend: a new tab in `SettingsTabs`, backed by a `useAnnotationClasses` hook over the generated TanStack Query client. Much of the frontend exists on the prototype branch and is ported, with tests added.

**Tech Stack:** FastAPI, SQLModel, pytest; SvelteKit (Svelte 5 runes), TanStack Query, vitest + @testing-library/svelte.

**Spec:** `.experimental/superpowers/specs/2026-10-26-annotation-classes-settings-tab-design.md`

**Prototype branch:** `michal-lig-11319-annotation-classes-in-settings-prototype` (abbreviated `PROTO` below). Port files with `git show PROTO:<path>`. Do **not** port its picker changes (`EditAnnotationClassesButton`, `NamePickerField`, `useCreateLabel`, `SelectList`, `LabelNotFound`, `useSettingsDialog` tab argument, …).

## Global Constraints

- Branch from `origin/main`, not from the current LIG-11301 branch. Two PRs: Tasks 1–3 (backend), then Tasks 4–8 (frontend), the second stacked on the first.
- Load the skills from `AGENTS.md` before editing: python-guide + backend-guide for `lightly_studio/src/**`, frontend-guide for `lightly_studio_view/**`, glossary for user-visible text.
- User-visible term is "annotation class" (never "label"). Evaluation run staleness is called "out of date" in the UI.
- No change to class pickers, Smart select, Find all instances, roles, tags, or annotation sources.
- Custom colors stay in browser memory via `useCustomLabelColors`; no database storage.
- Tab changes apply at once; they do not go through the dialog's "Save changes".
- The generated API client (`lightly_studio_view/src/lib/api/lightly_studio_local`) and `lightly_studio/openapi.json` are gitignored. After backend changes, regenerate locally: `cd lightly_studio && uv run python -m lightly_studio.export_schema` (check the module for the exact invocation), then `cd lightly_studio_view && npm run generate-api-client`.
- Validation per PR: backend `cd lightly_studio && make static-checks && uv run pytest <affected tests>`; frontend `cd lightly_studio_view && make static-checks && make test`.

## Review Focus

1. Renaming a class to a name that already exists in the dataset: the user expects an error toast and the old name kept, not an unhandled promise rejection or a 500 page. → Task 2 test (backend status), Task 7 test (row keeps old name when `onRename` rejects).
2. Deleting a class used by annotations in several collections (e.g. ground truth and predictions): all its annotations go and the runs of every affected collection go out of date. → Task 3 test.
3. Typing a partial name and pressing Enter: nothing is added. → Task 8 test.
4. Enter in any input of the tab must not submit the settings form (it would save and close the dialog). → Task 7 and Task 8 tests.
5. Opening the settings outside a dataset (no `collection_id` route param): the tab shows a hint and makes no request. → Task 8 test.

---

## PR 1: Backend

### Task 1: Share the "delete annotations and mark runs stale" logic

**Files:**
- Create: `lightly_studio/src/lightly_studio/services/annotations_service/delete_annotations_by_ids.py`
- Modify: `lightly_studio/src/lightly_studio/services/annotations_service/__init__.py`
- Modify: `lightly_studio/src/lightly_studio/api/routes/api/annotations/bulk_delete_annotations.py:90-106` (remove `_delete_annotations`, call the service)
- Test: `lightly_studio/tests/services/annotations_service/test_delete_annotations_by_ids.py`

**Interfaces:**
- Produces: `annotations_service.delete_annotations_by_ids(session: Session, annotation_ids: Sequence[UUID]) -> int` — deletes the annotations, marks the evaluation runs of their collections stale, returns the deleted count. Body moved verbatim from `_delete_annotations`.

- [ ] **Step 1: Write the failing test** `test_delete_annotations_by_ids__marks_evaluation_run_stale`: same setup as `test_bulk_delete_annotations__marks_evaluation_run_stale` in `tests/api/routes/api/annotations/test_bulk_delete_annotations.py:98`, but call the service with `[pred_annotation.sample_id]`; assert the return value is `1` and `run.stale_since is not None`.
- [ ] **Step 2: Run** `cd lightly_studio && uv run pytest tests/services/annotations_service/test_delete_annotations_by_ids.py -v` → FAIL (import error).
- [ ] **Step 3: Move** `_delete_annotations` into the service; both bulk delete routes return `BulkDeleteAnnotationsResult(deleted_count=annotations_service.delete_annotations_by_ids(...))`.
- [ ] **Step 4: Run** the new test and `tests/api/routes/api/annotations/test_bulk_delete_annotations.py` → PASS. Run `make static-checks`.
- [ ] **Step 5: Commit** `Share the bulk annotation delete logic as a service`.

### Task 2: List annotation classes with their annotation counts

**Files:**
- Create: `lightly_studio/src/lightly_studio/resolvers/annotation_label_resolver/get_annotation_counts.py` (port from PROTO)
- Modify: `lightly_studio/src/lightly_studio/resolvers/annotation_label_resolver/__init__.py`
- Modify: `lightly_studio/src/lightly_studio/models/annotation_label.py` (add `AnnotationLabelWithCountView`)
- Modify: `lightly_studio/src/lightly_studio/api/routes/api/annotation_label.py` (new route, port from PROTO)
- Test: `lightly_studio/tests/resolvers/annotation_label_resolver/test_get_annotation_counts.py` (port from PROTO), `lightly_studio/tests/api/routes/api/test_annotation_label.py`

**Interfaces:**
- Produces: `annotation_label_resolver.get_annotation_counts(session: Session, dataset_id: UUID) -> dict[UUID, int]` (labels without annotations map to 0).
- Produces: `class AnnotationLabelWithCountView(AnnotationLabelView): annotation_count: int`.
- Produces: `GET /api/collections/{collection_id}/annotation_labels_with_counts -> list[AnnotationLabelWithCountView]`; generated client `readAnnotationLabelsWithCountsOptions`.

- [ ] **Step 1: Write the failing tests.** Port `test_get_annotation_counts` and `test_read_annotation_labels_with_counts` from PROTO (expect `{"cat": 1, "dog": 0}` and `{cat: 2, dog: 0}`, other dataset's label excluded). Add `test_get_annotation_counts__counts_all_collections`: one label, one annotation in each of two annotation collections (`create_annotations(..., collection_name="ground_truth")` and `"predictions"`) → count `2`. Add `test_update_annotation_label__duplicate_name`: rename "dog" to existing "cat" via `PUT /api/annotation_labels/{id}` → assert a 4xx status (pin whatever the route returns today; if it raises a 500, make it return `HTTP_STATUS_CONFLICT` 409 with detail "Annotation label already exists").
- [ ] **Step 2: Run** `uv run pytest tests/resolvers/annotation_label_resolver/test_get_annotation_counts.py tests/api/routes/api/test_annotation_label.py -v` → new tests FAIL.
- [ ] **Step 3: Implement** the resolver, view model, and route (port from PROTO); fix the duplicate rename status if needed.
- [ ] **Step 4: Run** the tests → PASS; `make static-checks`.
- [ ] **Step 5: Commit** `List annotation classes with their annotation counts`.

### Task 3: Delete a class together with its annotations

**Files:**
- Create: `lightly_studio/src/lightly_studio/resolvers/annotation_resolver/get_ids_by_label_id.py`
- Modify: `lightly_studio/src/lightly_studio/resolvers/annotation_resolver/__init__.py`
- Modify: `lightly_studio/src/lightly_studio/api/routes/api/annotation_label.py:103-114` (`delete_annotation_label`)
- Test: `lightly_studio/tests/api/routes/api/test_annotation_label.py`, `lightly_studio/tests/resolvers/annotation_resolver/test_get_ids_by_label_id.py`

**Interfaces:**
- Consumes: `annotations_service.delete_annotations_by_ids` (Task 1).
- Produces: `annotation_resolver.get_ids_by_label_id(session: Session, label_id: UUID) -> list[UUID]` — the `sample_id`s of all annotations with that label, in any collection.
- Produces: `DELETE /api/annotation_labels/{label_id}`: 404 "Annotation label not found" before deleting anything; otherwise deletes the annotations via the service, then the label. Docstring: "Delete an annotation label and all annotations that use it."

- [ ] **Step 1: Write the failing tests.**
  - `test_get_ids_by_label_id`: two labels, annotations of both → returns only the first label's IDs (as a set).
  - `test_delete_annotation_label__deletes_its_annotations` (port from PROTO): remaining label IDs == `[dog_id]`.
  - `test_delete_annotation_label__marks_evaluation_runs_stale`: annotations of the label in `ground_truth` and `predictions` collections, an evaluation run on both (setup as in Task 1) → after delete, `stale_since is not None`; no annotation of the label remains.
  - `test_delete_annotation_label__not_found`: random UUID → 404.
- [ ] **Step 2: Run** `uv run pytest tests/api/routes/api/test_annotation_label.py tests/resolvers/annotation_resolver/test_get_ids_by_label_id.py -v` → FAIL.
- [ ] **Step 3: Implement** the resolver and the route change.
- [ ] **Step 4: Run** the tests plus `tests/resolvers/annotation_label_resolver/` → PASS; `make static-checks`.
- [ ] **Step 5: Commit** `Delete annotations together with their annotation class`, then open PR 1 (pull-requests skill).

---

## PR 2: Frontend

Before starting: regenerate `openapi.json` and the API client (Global Constraints).

### Task 4: Color picker works inside a modal dialog

**Files:**
- Modify: `lightly_studio_view/src/lib/components/ui/color-picker/color-picker.svelte` (port the PROTO diff: portal into the closest `[role="dialog"]`, offset by a transformed ancestor, `pointer-events-auto`)

- [ ] **Step 1: Port** the diff (`git diff origin/main PROTO -- lightly_studio_view/src/lib/components/ui/color-picker`).
- [ ] **Step 2: Verify** existing color picker uses still work: `make test` in `lightly_studio_view` passes. Manual check happens in Task 8.
- [ ] **Step 3: Commit** `Fix the color picker inside a modal dialog`.

### Task 5: `useAnnotationClasses` hook

**Files:**
- Create: `lightly_studio_view/src/lib/components/Settings/AnnotationClassesTab/useAnnotationClasses.svelte.ts` (port from PROTO)
- Test: `lightly_studio_view/src/lib/components/Settings/AnnotationClassesTab/useAnnotationClasses.svelte.test.ts`

**Interfaces:**
- Produces: `useAnnotationClasses(getParams: () => { collectionId: string; datasetId: string }) => { query, addClass(name: string): Promise<AnnotationLabel>, renameClass(labelId: string, oldName: string, name: string): Promise<void>, deleteClass(labelId: string): Promise<unknown> }`. `query.data` is `AnnotationLabelWithCountView[]`. The query is disabled while `collectionId` is empty.
- Error toasts: "Could not add the annotation class.", "Could not rename the annotation class.", "Could not delete the annotation class."

- [ ] **Step 1: Write the failing tests** (mock `@tanstack/svelte-query` `createMutation` to return `{ mutateAsync }` spies and `useCustomLabelColors`):
  - `renameClass moves the custom color to the new name`: `getCustomColor('cat')` returns a color → `setCustomColor('kitty', color, alpha)` and `deleteCustomColor('cat')` called.
  - `renameClass keeps colors when the rename fails`: `mutateAsync` rejects → `setCustomColor` not called, promise rejects.
  - `query is disabled without a collection`: `collectionId: ''` → query options have `enabled: false`.
- [ ] **Step 2: Run** `npx vitest run src/lib/components/Settings/AnnotationClassesTab/useAnnotationClasses.svelte.test.ts` → FAIL.
- [ ] **Step 3: Port** the hook from PROTO; add `enabled: !!getParams().collectionId` to the query options.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `Add a hook to manage annotation classes`.

### Task 6: Delete confirmation dialog

**Files:**
- Create: `lightly_studio_view/src/lib/components/Settings/AnnotationClassesTab/DeleteAnnotationClassDialog/{DeleteAnnotationClassDialog.svelte,index.ts}` (port from PROTO)
- Test: `.../DeleteAnnotationClassDialog/DeleteAnnotationClassDialog.test.ts`

**Interfaces:**
- Produces: props `{ open: boolean (bindable); name: string; annotationCount: number; onConfirm: () => Promise<unknown> }`.

- [ ] **Step 1: Write the failing tests:**
  - with `annotationCount: 3`: text "This also deletes 3 annotations", text "Evaluation runs of these annotations become out of date.", button "Delete class and 3 annotations".
  - with `annotationCount: 0`: text "No annotations use this class.", no out-of-date warning, button "Delete annotation class".
  - confirm calls `onConfirm` once and closes; when `onConfirm` rejects, the dialog stays open.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Port** the dialog and add the out-of-date sentence after the annotation count (only when `annotationCount > 0`, because no runs change otherwise).
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `Add the delete annotation class dialog`.

### Task 7: Annotation class row

**Files:**
- Create: `lightly_studio_view/src/lib/components/Settings/AnnotationClassesTab/AnnotationClassRow/{AnnotationClassRow.svelte,index.ts}` (port from PROTO)
- Test: `.../AnnotationClassRow/AnnotationClassRow.test.ts`

**Interfaces:**
- Consumes: `DeleteAnnotationClassDialog` (Task 6).
- Produces: props `{ name: string; annotationCount: number; isHighlighted?: boolean; onRename: (name: string) => Promise<unknown>; onDelete: () => Promise<unknown> }`.

- [ ] **Step 1: Write the failing tests:**
  - shows name and "1 annotation" / "2 annotations".
  - rename: click "Rename cat", type "kitty", Enter → `onRename('kitty')`; the keydown event is `defaultPrevented` (does not submit the form).
  - Escape cancels: `onRename` not called, name "cat" shown.
  - unchanged or blank name → `onRename` not called.
  - `onRename` rejects → no unhandled rejection, name "cat" shown.
  - click "Delete cat" → dialog opens.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Port** the row; wrap `await onRename(trimmed)` in try/catch (the hook already shows the toast).
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `Add the annotation class row`.

### Task 8: Annotation classes tab in the settings

**Files:**
- Create: `lightly_studio_view/src/lib/components/Settings/AnnotationClassesTab/{AnnotationClassesTab.svelte,index.ts}` (port from PROTO)
- Modify: `lightly_studio_view/src/lib/components/Settings/SettingsTabs/SettingsTabs.svelte` (add `{ value: 'annotation-classes', label: 'Annotation classes', component: AnnotationClassesTab }` last)
- Modify: `lightly_studio_view/src/lib/components/Settings/SettingsDialog.svelte` (footer: on the `annotation-classes` tab show "Changes save immediately." and a "Close" button instead of "Cancel"/"Save changes"; port from PROTO, without the `settingsDialogTab` change)
- Test: `.../AnnotationClassesTab/AnnotationClassesTab.test.ts`, `lightly_studio_view/src/lib/components/Settings/SettingsDialog.test.ts`

**Interfaces:**
- Consumes: `useAnnotationClasses` (Task 5), `AnnotationClassRow` (Task 7). Reads `page.params.collection_id` and `page.params.dataset_id` from `$app/state`.

- [ ] **Step 1: Write the failing tests** (mock `useAnnotationClasses` with classes `bear` (2), `cat` (0); mock `$app/state` as in `NavigationMenu.test.ts`):
  - lists classes sorted by name with "2 of …"-style count text when filtered.
  - typing "bea" + Enter → `addClass` not called; the Enter keydown is `defaultPrevented`.
  - typing "wolf" + Enter → `addClass('wolf')`; input cleared.
  - typing "Bear" → "already exists" text, no add row.
  - no `collection_id` → "Open a dataset to manage its annotation classes." and no rows.
  - `SettingsDialog.test.ts`: opening the "Annotation classes" tab shows "Close" and "Changes save immediately.", and no "Save changes".
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Port** the tab, register it, change the footer.
- [ ] **Step 4: Run** `make static-checks && make test` → PASS.
- [ ] **Step 5: Manual check** with the run skill: add, find, rename, change a color (picker opens inside the dialog and is clickable), delete a used class (modal text, annotations gone, class pickers updated).
- [ ] **Step 6: Commit** `Add the annotation classes tab to the settings`, then open PR 2 stacked on PR 1.
