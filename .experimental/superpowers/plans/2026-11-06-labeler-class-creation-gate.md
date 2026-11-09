# Only Editors Create Annotation Classes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Users below the editor role can only pick existing annotation classes; they cannot create one from a class picker or by saving.

**Architecture:** One hook holds the role rule. `SelectList` gets an opt-in `allowCreate` prop that every class picker sets from the hook. `useCreateLabel` refuses to send the request below editor and rejects with a typed error. It shows no message; the caller that owns the user action shows the error text.

**Tech Stack:** SvelteKit, Svelte 5 runes, TanStack Query, vitest + testing-library, svelte-sonner.

**Spec:** `.experimental/superpowers/specs/2026-11-05-labeler-class-creation-gate-design.md`

## Global Constraints

- Frontend only. No backend change.
- Rule: `hasMinimumRole(user?.role, 'editor')`. No role (local mode) → allowed. Editor and admin → no change.
- Empty-search text: `No class found.`
- Save-guard error text: `Class "X" is no longer available. Choose another class.` (X = the class name). Callers show it; `useCreateLabel` does not.
- Drop "or create" from picker text only when creation is not allowed.
- Bulk classification: gate the class field only, not the annotation source field.
- SAM3 prompt, tags, captions, annotation sources: unchanged.
- Load `frontend-guide` before editing; `glossary` for user-facing text; `changelog` for Task 5.
- Commits: show the diff and commit only after the user approves.
- Existing tests that break because of the new role rule or the new error: fix their setup (mocks, role), not the behavior. Tests that create a class through a picker run as `editor`.
- Validate in `lightly_studio_view`: `npx vitest run <file>`; at the end `make static-checks && make test`.
- One PR per task (Tasks 4 and 5 share one), stacked in order (see PRs). Each PR's branch starts from the previous PR's branch.

## PRs

The stack starts on PR 0, which adds the spec and this plan. Each PR branches from the one before it.

| PR | Tasks | Branch | Est. LOC |
|---|---|---|---|
| 0 | Spec and plan | `michal-lig-11356-0-plan` | ~250 (docs) |
| 1 | 1: `useCanCreateAnnotationClass` hook | `michal-lig-11356-1-class-creation-hook` | ~40 |
| 2 | 2: `SelectList` `allowCreate`, `LabelNotFound` text | `michal-lig-11356-2-select-list-allow-create` | ~85 |
| 3 | 3: Wire every class picker | `michal-lig-11356-3-gate-class-pickers` | ~140 |
| 4 | 4 + 5: Save guard, its callers, changelog | `michal-lig-11356-4-class-creation-save-guard` | ~200 |

## Review Focus

- Typing an existing name in another case ("Cat" for "cat") and pressing Enter still selects the existing class under the gate. → Task 2 test.
- Local mode (no role) still shows the "Create: …" row and creates on Enter. → Task 1 and Task 2 tests (default prop).
- A viewer is treated like a labeler. → Task 1 test.
- A labeler brushing with a deleted class leaves overlapping masks untouched; an editor's empty stroke still creates no class. → Task 4 tests.
- A rejected class creation shows exactly one message, the class error text, in every caller. → Task 4 tests.
- A labeler draws a box before the class list has loaded. An existing class must not count as missing, or the drawing is lost. `useCreateCuboidAnnotation` waits for the list with `labels.refetch()`; `SampleObjectDetectionRect` does not. → Reviewer checks Task 4.

---

### Task 1: `useCanCreateAnnotationClass` hook

**Files:**
- Create: `lightly_studio_view/src/lib/hooks/useCanCreateAnnotationClass/useCanCreateAnnotationClass.ts`
- Create: `lightly_studio_view/src/lib/hooks/useCanCreateAnnotationClass/useCanCreateAnnotationClass.test.ts`
- Modify: `lightly_studio_view/src/lib/hooks/index.ts` (export it)

**Interfaces:**
- Consumes: `useAuth()` from `$lib/hooks/useAuth/useAuth`, `hasMinimumRole` from `$lib/hooks/useAuth/hasMinimumRole`.
- Produces: `useCanCreateAnnotationClass(): boolean`.

- [ ] **Step 1: Write the failing tests** — mock `$lib/hooks/useAuth/useAuth` (see `NavigationMenu.test.ts`). Table test:

```ts
it.each([
    [undefined, true],
    ['admin', true],
    ['editor', true],
    ['labeler', false],
    ['viewer', false]
])('role %s → %s', (role, expected) => {
    vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: !!role,
        user: role ? { role, email: 'a@b.c' } : undefined
    } as ReturnType<typeof useAuth>);
    expect(useCanCreateAnnotationClass()).toBe(expected);
});
```

- [ ] **Step 2:** `npx vitest run src/lib/hooks/useCanCreateAnnotationClass` → FAIL (module not found).
- [ ] **Step 3: Implement** `useCanCreateAnnotationClass(): boolean` — `hasMinimumRole(useAuth().user?.role, 'editor')`. Short docstring naming the rule.
- [ ] **Step 4:** Same command → PASS.
- [ ] **Step 5:** Show diff, commit on approval: `feat: add useCanCreateAnnotationClass hook (LIG-11356)`.

### Task 2: `SelectList` `allowCreate` prop and `LabelNotFound` text

**Files:**
- Modify: `lightly_studio_view/src/lib/components/SelectList/SelectList.svelte`
- Modify: `lightly_studio_view/src/lib/components/SelectList/SelectList.test.ts`
- Modify: `lightly_studio_view/src/lib/components/LabelNotFound/LabelNotFound.svelte`

**Interfaces:**
- Produces: `SelectList` prop `allowCreate?: boolean` (default `true`). `LabelNotFound` prop `allowCreate?: boolean` (default `true`); when `false` it renders `No class found.`

Behavior with `allowCreate={false}`:
- The "Create: …" row is not rendered.
- Enter with no highlighted item: if the input matches an existing item case-insensitively, select it (both the `onKeyboardConfirm` branch and the other branch, as today); otherwise do nothing and do not `items.push`.
- Arrow keys and selecting listed items: unchanged.

- [ ] **Step 1: Write the failing tests** in `SelectList.test.ts` (items `item1..3` as in the file; open the popover via the trigger, type in `select-list-input`):
  - `hides the create row when allowCreate is false` — type `zebra`; `queryByText('Create:')` is null.
  - `does not create an item on Enter when allowCreate is false` — type `zebra{Enter}`; `onSelect` not called.
  - `does not confirm a new item on Enter when allowCreate is false` — with `onKeyboardConfirm`, type `zebra{Enter}`; neither `onSelect` nor `onKeyboardConfirm` called.
  - `selects an existing item typed in another case when allowCreate is false` — with `onKeyboardConfirm`, type `ITEM2{Enter}`; `onKeyboardConfirm` called with `{ value: 'item2', label: 'Item 2' }`. cmdk filters case-insensitively and highlights the first match, so this goes through the highlighted path, not the fallback branches in `handleKeyDown`. Those are likely unreachable for existing items; the test only pins that the gate does not block picking an existing class.
  - `shows the create row by default` — no `allowCreate`; type `zebra`; `getByText('Create:')` present.
- [ ] **Step 2:** `npx vitest run src/lib/components/SelectList` → new tests FAIL.
- [ ] **Step 3: Implement** the prop in `SelectList.svelte`: wrap the create row in `allowCreate &&`; in `handleKeyDown`, only create a new item when `allowCreate`. Add `allowCreate` to `LabelNotFound.svelte`.
- [ ] **Step 4:** Same command → PASS.
- [ ] **Step 5:** Show diff, commit on approval: `feat: let SelectList hide class creation (LIG-11356)`.

### Task 3: Wire every class picker

**Files (modify, all under `lightly_studio_view/src/lib/components/`):**
- `SampleDetails/AnnotationClassSelect/AnnotationClassSelect.svelte`
- `SelectClassDialog/SelectClassDialog.svelte` (+ `SelectClassDialog.test.ts`)
- `FrameAnnotationsPanel/FrameAnnotationsPanel.svelte`
- `AnnotationDetails/AnnotationDetailsPanel/AnnotationMetadata/AnnotationMetadataLabel/AnnotationMetadataLabel.svelte`
- `SampleDetails/SampleDetailsSidePanel/SampleDetailsSidePanelAnnotation/SampleDetailsSidePanelAnnotation.svelte`
- `SampleDetails/SampleDetailsClassificationSegment/SampleDetailsClassificationSegment.svelte` (both pickers)
- `PointCloudLabelingWorkspace/CuboidLayer/PointCloudAnnotationDetails/PointCloudAnnotationLabel/PointCloudAnnotationLabel.svelte`
- `AnnotationsGrid/SelectedAnnotations/SelectedAnnotations.svelte`
- `BulkClassificationPanel/NamePickerField/NamePickerField.svelte`, `BulkClassificationPanel/BulkClassificationPanel.svelte`

**Interfaces:**
- Consumes: `useCanCreateAnnotationClass()` (Task 1), `allowCreate`, `LabelNotFound canCreate` (Task 2).
- Produces: `NamePickerField` prop `allowCreate?: boolean` (default `true`); passes it to `SelectList` and, when `false`, uses placeholder `Search…` and a `notFound` snippet with `<LabelNotFound label={inputValue} allowCreate={false} />`. Only the class field in `BulkClassificationPanel` sets it.

In each picker: `const canCreateClass = useCanCreateAnnotationClass();`, pass `allowCreate={canCreateClass}`, render `<LabelNotFound label={inputValue} allowCreate={canCreateClass} />` in `notFound` (add the snippet where missing: `AnnotationClassSelect`, `SelectClassDialog`). Text when `!canCreateClass`:

| Current | Gated |
|---|---|
| `Select or create a class` | `Select a class` |
| `Choose or create a class` | `Choose a class` |
| `Select or create a class for a new annotation.` | `Select a class for a new annotation.` |
| `Search or create a class...` | `Search a class...` |
| `Choose an existing class or type a new one to create it.` | `Choose an existing class.` |

- [ ] **Step 1: Write the failing tests** in `SelectClassDialog.test.ts`, mocking `$lib/hooks/useCanCreateAnnotationClass/useCanCreateAnnotationClass`:
  - `hides class creation below editor` — hook returns `false`; type `zebra`; no `Create:` text; `getByText('No class found.')` present; `getByText('Choose an existing class.')` present; `zebra{Enter}` does not call `onConfirm`.
  - `keeps class creation for editors` — hook returns `true`; type `zebra`; `Create:` present.
- [ ] **Step 2:** `npx vitest run src/lib/components/SelectClassDialog` → FAIL.
- [ ] **Step 3: Implement** the wiring in all listed files.
- [ ] **Step 4:** Same command → PASS. Then run the existing tests of every touched component (`npx vitest run src/lib/components/{SelectClassDialog,FrameAnnotationsPanel,AnnotationDetails,SampleDetails,PointCloudLabelingWorkspace,AnnotationsGrid,BulkClassificationPanel}`) → PASS. Fix broken existing tests per Global Constraints.
- [ ] **Step 5:** Show diff, commit on approval: `feat: hide class creation in pickers below editor (LIG-11356)`.

### Task 4: Save guard in `useCreateLabel` and its callers

`useCreateLabel` only rejects. It shows no message. The caller that owns the user action shows the message.

**Files:**
- Modify: `lightly_studio_view/src/lib/hooks/useCreateLabel/useCreateLabel.ts`
- Create: `lightly_studio_view/src/lib/hooks/useCreateLabel/useCreateLabel.test.ts`
- Modify: `lightly_studio_view/src/lib/hooks/useSegmentationMaskBrush.ts` (+ `.test.ts`)
- Modify: `lightly_studio_view/src/lib/components/SampleDetails/SampleDetailsClassificationSegment/SampleDetailsClassificationSegment.svelte` (+ `.test.ts`)
- Modify (use the error text instead of the fixed message): `lightly_studio_view/src/lib/components/SampleDetails/SampleObjectDetectionRect/SampleObjectDetectionRect.svelte`, `lightly_studio_view/src/lib/components/VideoDetails/VideoDetails.svelte`, `lightly_studio_view/src/lib/components/PointCloudLabelingWorkspace/useCreateCuboidAnnotation/useCreateCuboidAnnotation.svelte.ts` (+ `.svelte.test.ts`)
- No change: `SmartSelectOverlay/useSmartSelect.svelte.ts` and `FindInstancesOverlay/useFindInstances.svelte.ts`. They already show `getAnnotationPreviewErrorMessage(error)`, which returns `error.message`.

**Interfaces:**
- Consumes: `useCanCreateAnnotationClass()` (Task 1).
- Produces, all in `useCreateLabel.ts`:
  - `export class AnnotationClassNotAvailableError extends Error`, `constructor(className: string)`, message `Class "X" is no longer available. Choose another class.`
  - `getCreateLabelErrorMessage(error: unknown, fallback: string): string` → `error.message` for `AnnotationClassNotAvailableError`, else `fallback`.
  - `useCreateLabel` returns `{ createLabel, canCreateLabel: boolean }`. `createLabel` signature unchanged. Below editor it sends no request, shows nothing and rejects with `AnnotationClassNotAvailableError`.

- [ ] **Step 1: Write the failing tests.**
  - `useCreateLabel.test.ts`:
    - `rejects without a request below editor`: hook `false`. `createLabel({ dataset_id: 'd', annotation_label_name: 'cat' })` rejects with `AnnotationClassNotAvailableError` and message `'Class "cat" is no longer available. Choose another class.'`. `mutate` is not called. `toast.error` is not called. `canCreateLabel` is `false`.
    - `creates the class for editors`: hook `true`. `mutate` is called with `{ path: { collection_id: 'c1' }, body: {...} }` and resolves with the `onSuccess` data.
    - `getCreateLabelErrorMessage`: returns the error text for `AnnotationClassNotAvailableError('cat')`, and `'fallback'` for `new Error('x')`.
  - `useSegmentationMaskBrush.test.ts`:
    - `stops before trimming other masks when the class cannot be created`: below editor, selected class `car` does not exist. `finishBrush` resolves. `toast.error` is called with `'Class "car" is no longer available. Choose another class.'`. `applySegmentationMaskConstraints`, `createLabel` and `createAnnotation` are not called.
    - `creates no class for an empty mask`: editor, new label `car`, empty mask. `createLabel` is not called. This pins today's order for editors.
  - `SampleDetailsClassificationSegment.test.ts`:
    - `shows the class error when the class cannot be created`: as `editor`, so the picker lets the new name through; `createLabel` rejects with `AnnotationClassNotAvailableError('zebra')`. Pick `zebra`. `createLabel` is called. `createAnnotation` is not called. `toast.error` is called once, with `'Class "zebra" is no longer available. Choose another class.'`.
  - `useCreateCuboidAnnotation.svelte.test.ts`:
    - `shows the class error when the class cannot be created`: `createLabel` rejects with `AnnotationClassNotAvailableError('car')`. `toast.error` is called once, with the error text.
    - `asks for a class again after the remembered class was rejected`: remembered class `car` is rejected as above. On the next attempt, `requestLabel` is called.
- [ ] **Step 2:** `cd lightly_studio_view && npx vitest run src/lib/hooks/useCreateLabel src/lib/hooks/useSegmentationMaskBrush.test.ts src/lib/components/SampleDetails/SampleDetailsClassificationSegment src/lib/components/PointCloudLabelingWorkspace/useCreateCuboidAnnotation` → the new tests FAIL.
- [ ] **Step 3: Implement.**
  - `useCreateLabel`: read the Task 1 hook once at setup and return it as `canCreateLabel`. Below editor, reject with `new AnnotationClassNotAvailableError(name)`. Do not call `mutate`. Do not show a toast.
  - Mask brush: keep today's order. Move only the label lookup up, before `applySegmentationMaskConstraints`. For the create path (`!selectedAnnotation`), if no label is found and `!canCreateLabel`, show `toast.error(new AnnotationClassNotAvailableError(name).message)`, call `refetch()` and return. `createLabel` stays where it is, after the empty-mask check.
  - Classification segment: move the label lookup and `createLabel` inside the `try`. In `catch`, show `getCreateLabelErrorMessage(error, 'Failed to create classification. Please try again.')`.
  - `SampleObjectDetectionRect`, `VideoDetails`, `useCreateCuboidAnnotation`: in each `catch`, pass the current fixed message as `fallback` to `getCreateLabelErrorMessage`. Keep `console.error`.
  - `useCreateCuboidAnnotation` also: on `AnnotationClassNotAvailableError`, forget the remembered class for the collection, so the next attempt opens the class dialog. Today `selectAnnotationLabel` returns the remembered class without asking, so a labeler would be stuck.
- [ ] **Step 4:** Same command → PASS, including the existing tests. Also run `npx vitest run src/lib/components/SampleDetails/SampleObjectDetectionRect src/lib/components/VideoDetails src/lib/components/SampleDetails/SmartSelectOverlay src/lib/components/SampleDetails/FindInstancesOverlay` → PASS.
- [ ] **Step 5:** Show the diff. Commit when the user approves: `feat: block class creation on save below editor (LIG-11356)`.

### Task 5: Changelog and full checks

**Files:**
- Modify: `CHANGELOG.md` (follow the `changelog` skill; one entry: only editors can create annotation classes in the labeling tools).

- [ ] **Step 1:** Add the entry.
- [ ] **Step 2:** `cd lightly_studio_view && make static-checks && make test` → all pass.
- [ ] **Step 3:** Show diff, commit on approval: `docs: changelog for class creation gate (LIG-11356)`.
