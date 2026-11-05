# Annotation Class Colors in the DB Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Spec:** `.experimental/superpowers/specs/2026-11-03-annotation-class-colors-in-db-design.md`

## Goal

Save custom annotation class colors per dataset in the database, so all users of a dataset
see them after a reload. "Reset to default" in the color picker (PR 9) is parked; see PR 9.

## Architecture

**Backend**
- Nullable `color` and `alpha` columns on `annotation_label`.
- A `PUT /annotation_labels/{label_id}/color` endpoint to set or clear them.

**Frontend**
- One factory makes two color stores: one for annotation classes, one for annotation sources.
- Each store has two layers:
  - a **saved** layer, loaded from the class list;
  - a **preview** layer, owned by one open color picker.
- Apply saves the preview, Cancel discards it. A class list refetch replaces only the saved layer.

**Tech stack:** FastAPI, SQLModel, Alembic (PostgreSQL), DuckDB (`create_all`), SvelteKit,
Svelte 5, TanStack Query, hey-api generated client, vitest, pytest.

## Global Constraints

**Behavior**
- Colors are per dataset, not per user. `color`/`alpha` are nullable; null means the
  default (hashed palette) color.
- A rename must not clear the color.
- `color`/`alpha` live on `AnnotationLabelTable` and `AnnotationLabelView` only, not on
  `AnnotationLabelBase` or `AnnotationLabelCreate`: a color is set later through its own
  endpoint, not when a class is created. The `create_annotation_label` test helper does not take them either.
- Class colors and source colors never share a map:
  - call sites that color by source use `getColorBySource` and the source store;
  - all others use `getColorByLabel` and the class store.
- The preview is local:
  - Apply saves it, Cancel discards it.
  - A refetch of the same dataset keeps it; a dataset change clears it.
  - A failed save shows a toast and reverts to the saved color.
- Existing DuckDB files are not upgraded (as in #2782). PR 1 adds a CHANGELOG note.
- User-facing text says "annotation class" and "annotation source", never "label".

**Out of scope:** saving source colors (they stay browser-only), live updates from other
users, export/import of colors.

**Process**
- Load skills before editing:
  - `python-guide` + `backend-guide` for `lightly_studio/**`
  - `frontend-guide` for `lightly_studio_view/**`
  - `best-practices` for new modules, `changelog` for `CHANGELOG.md`, `glossary` for user-facing text
  - `pull-requests` before each PR
- Frontend tests have no `QueryClientProvider`. Stub hooks that use TanStack Query
  (see `VideoDetails.test.ts`).
- Each PR stays under ~200 changed lines, not counting `lightly_studio_view/src/lib/api/**`
  and lockfiles.
- Commit and push only on request. Never force push.
- Validation:
  - Backend: `cd lightly_studio && make static-checks && uv run pytest <tests>`.
    Migration PRs also run `make migration-check-postgresql`.
  - Frontend: `cd lightly_studio_view && make static-checks && make test`.

## Decisions

- **Plots keep `getColorByLabel`.** A class with the same name as a plot category recolors
  it, as today.
- **The frontend keys colors by class name, the server by class ID.** A refetch after a
  rename moves the color to the new name. A picker session keeps the name it started with
  (PR 6), so a rename while a preview is open leaves no stray preview. Keying the frontend
  store by ID would touch every color reader for no extra gain.
- **The save hook is stubbed per test file** (PR 11), not globally in `src/setupTests.ts`,
  so tests that need the real hook still get it.
- **Accepted gap: cancelling a second preview while the first save is pending.** Apply A,
  then preview and cancel B before A's save finishes: the swatch shows the color saved
  before A until A's save finishes, then A. The gap lasts one request; tracking pending
  saves apart from the open preview is not worth the extra state.

## Review Focus

Cases that no single test covers end to end. Check them during review.

1. **The class list refetches while a class picker is open.**
   The preview stays, and Apply saves it. *Test: PR 12.*
2. **The user reopens the picker while a save is pending, or applies twice quickly.**
   The first save does not clear the second preview. An older save that finishes late does
   not overwrite a newer one, in the browser or on the server. *Tests: PRs 10, 11.*
3. **The user switches dataset while a preview is open, a save is pending, or the new class
   list is still loading.** No color, preview or class ID of the old dataset is used in the
   new one. *Tests: PRs 10, 11, 12.*
4. **An annotation source and an annotation class have the same name** (e.g. `"Predictions"`).
   Changing one never changes the other. *Tests: PRs 7, 8.*
5. **A save fails** (network error, class deleted meanwhile, class missing from the
   loaded list). A toast shows, and the swatch shows the saved color. *Tests: PRs 10, 11.*

---

## PR stack

PR 1 is based on `main`. Each next PR is based on the
previous one, except PR 9 (off the stack) and PR 10 (based on `main`). Every PR leaves the app working.

**Backend**

| # | Title | Branch | Est. LOC |
|---|-------|--------|----------|
| 1 | Add color columns to annotation classes | `michal-lig-11355-01-color-columns` | ~90 |
| 2 | Add a resolver to set an annotation class color | `michal-lig-11355-02-set-color-resolver` | ~115 |
| 3 | Add an endpoint to set an annotation class color | `michal-lig-11355-03-set-color-endpoint` | ~110 (+ generated) |

**Frontend prefactors** (no user-visible change, except the bug fix in PR 4)

| # | Title | Branch | Est. LOC |
|---|-------|--------|----------|
| 4 | Fix the annotation class color picker seed and button name | `michal-lig-11355-04-seed-legend-picker` | ~65 |
| 5 | Extract the custom color store into a factory | `michal-lig-11355-05-color-store-factory` | ~130 (moved code) |
| 6 | Keep color previews in a separate layer | `michal-lig-11355-06-preview-layer` | ~170 |
| 7 | Color annotations by source through getColorBySource | `michal-lig-11355-07-get-color-by-source` | ~145 |
| 8 | Keep annotation source colors in their own store | `michal-lig-11355-08-source-color-store` | ~110 |
| 8b | Pass the source name to AnnotationCanvas in its own field | `michal-lig-11355-08b-canvas-source-name` | ~90 |
| 9 | Add "Reset to default" to the color picker (off the stack) | `michal-lig-11355-09-reset-to-default` | ~120 |
| 10 | Let the color picker save changes asynchronously | `michal-lig-11355-10-async-color-save` | ~140 |

**Frontend feature**

| # | Title | Branch | Est. LOC |
|---|-------|--------|----------|
| 11 | Save annotation class colors in the dataset | `michal-lig-11355-11-save-class-colors` | ~195 |
| 12 | Load annotation class colors from the dataset | `michal-lig-11355-12-load-class-colors` | ~125 |

PR 8b was added after PRs 1–8 were open.

PR 9 is off the stack while we decide whether we want the feature. It stays open on `main`;
PR 10 is based on `main` and PRs 10–12 do not use it.

PR 12 must come after PR 11: loading colors without saving them would wipe the colors set in
the current session on every refetch.

LOC counts additions plus deletions, tests included, generated files excluded.

---

## PR 1: Add color columns to annotation classes

**Files:**
- Modify: `lightly_studio/src/lightly_studio/models/annotation_label.py`
- Modify: `lightly_studio/src/lightly_studio/api/routes/api/annotation_label.py` (`read_annotation_labels_with_counts`)
- Create: `lightly_studio/src/lightly_studio/migrations/versions/<generated>_add_annotation_label_color.py`
- Modify: `CHANGELOG.md`
- Test: `lightly_studio/tests/api/routes/api/test_annotation_label.py`, `lightly_studio/tests/resolvers/dataset_resolver/test_deep_copy.py`

**Interfaces:**
- Produces: `color: str | None = None` and `alpha: float | None = None` on `AnnotationLabelTable` and `AnnotationLabelView` (so `AnnotationLabelWithCountView` has them too).

- [ ] **Step 1: Write failing tests**
  - `test_get_annotation_labels__color`: set `color = "#ff8040"`, `alpha = 0.5` on a label and commit. Both `GET .../annotation_labels` and `GET .../annotation_labels_with_counts` return them; a label without a color returns `None` for both.
  - `test_deep_copy__annotation_label_color`: the copied label keeps `color`/`alpha`.
- [ ] **Step 2: Run** `cd lightly_studio && uv run pytest tests/api/routes/api/test_annotation_label.py tests/resolvers/dataset_resolver/test_deep_copy.py -k color`. Expected: FAIL.
- [ ] **Step 3: Add the fields.** Table comment: `# Custom display color as "#rrggbb", and its opacity in [0, 1]. Null means the default color.` Pass `color=label.color, alpha=label.alpha` in `read_annotation_labels_with_counts`.
- [ ] **Step 4: Generate the migration** with `make start-postgres && make migration-revision-postgresql MSG=add_annotation_label_color`. `down_revision` is the current head (`b7d24e8f913a` today; check `uv run alembic heads`). Keep only `add_column` for `color` (`AutoString()`, nullable) and `alpha` (`sa.Float()`, nullable); `downgrade` drops both.
- [ ] **Step 5: CHANGELOG** `### Changed`: `- BREAKING: DuckDB databases created before this version are not upgraded and fail to open. Re-index your data.`
- [ ] **Step 6: Verify** tests, `make migration-check-postgresql` and `make static-checks` pass. Commit on request.

## PR 2: Add a resolver to set an annotation class color

**Files:**
- Create: `lightly_studio/src/lightly_studio/resolvers/annotation_label_resolver/set_color.py`
- Modify: `lightly_studio/src/lightly_studio/resolvers/annotation_label_resolver/__init__.py`
- Test: `lightly_studio/tests/resolvers/annotation_label_resolver/test_set_color.py`, `test_update.py`

**Interfaces:**
- Produces: `annotation_label_resolver.set_color(session: Session, label_id: UUID, color: str | None, alpha: float | None) -> AnnotationLabelTable | None`. Returns `None` for an unknown label; commits and refreshes like `update.py`. No validation here (PR 3 does it).

- [ ] **Step 1: Write failing tests:** `test_set_color` (returned and re-read label have the values), `test_set_color__clear` (`None`/`None` clears both), `test_set_color__unknown_label` (→ `None`), `test_update__keeps_color` (a rename keeps `color`/`alpha`).
- [ ] **Step 2: Run** `uv run pytest tests/resolvers/annotation_label_resolver -k color`. Expected: FAIL.
- [ ] **Step 3: Implement** `set_color`.
- [ ] **Step 4: Verify** tests and `make static-checks` pass. Commit on request.

## PR 3: Add an endpoint to set an annotation class color

**Files:**
- Modify: `lightly_studio/src/lightly_studio/api/routes/api/annotation_label.py`
- Test: `lightly_studio/tests/api/routes/api/test_annotation_label.py`
- Generated (gitignored, regenerate locally): `lightly_studio_view/src/lib/api/lightly_studio_local/**`

**Interfaces:**
- Consumes: `annotation_label_resolver.set_color` (PR 2).
- Produces:
  - `AnnotationLabelColorRequest(BaseModel)`: `color: str | None = Field(pattern=r"^#[0-9a-fA-F]{6}$")`, `alpha: float | None = Field(ge=0, le=1)` (required but nullable, so an empty body does not clear the color), and a `model_validator(mode="after")` that raises `PydanticCustomError` unless both are set or both are `None` (a plain `ValueError` makes the app's validation handler return 500).
  - `PUT /annotation_labels/{label_id}/color` → `set_annotation_label_color(label_id: UUID, color_input: AnnotationLabelColorRequest, session: SessionDep) -> AnnotationLabelTable`; raises `NotFoundError("Annotation label not found")` for an unknown label.
  - Generated client: `setAnnotationLabelColor`, `setAnnotationLabelColorMutation`; `AnnotationLabelTable` gets `color?: string | null`, `alpha?: number | null`.

- [ ] **Step 1: Write failing tests:** `test_set_annotation_label_color` (200, a GET returns the values), `test_set_annotation_label_color__clear`, `test_set_annotation_label_color__not_found` (404), `test_update_annotation_label__keeps_color` (set via the endpoint, rename via `PUT /annotation_labels/{id}`, color stays), and `test_set_annotation_label_color__invalid` (422) parametrized over `{"color": "red", "alpha": 1}`, `{"color": "#ff8040", "alpha": 1.5}`, `{"color": "#ff8040", "alpha": null}`, `{"color": null, "alpha": 0.5}`.
- [ ] **Step 2: Run** them. Expected: FAIL.
- [ ] **Step 3: Implement** the request model and route.
- [ ] **Step 4: Verify** tests and `make static-checks` pass.
- [ ] **Step 5: Regenerate the client:** `make export-schema`, then `npm run generate-api-client` in `lightly_studio_view`, then `make static-checks` there. Commit on request.

---

## PR 4: Fix the annotation class color picker seed and button name

**Purpose:** Two fixes in the class color legend:
- It seeds the picker with alpha `0.4` for a class without a custom color, so Apply without changes dims the class.
- Its picker button has no accessible name, so a screen reader cannot tell which class it changes (CodeRabbit on #3018).

**Files:**
- Modify: `lightly_studio_view/src/lib/components/AnnotationColorLegend/AnnotationColorLegend.svelte`, `AnnotationColorLegend.test.ts`
- Modify: `lightly_studio_view/src/lib/components/ui/color-picker/color-picker.svelte`, `color-picker.test.ts`

Delete `getInitialColor`, `getInitialAlpha` and the destructured `getCustomColor`/`hasCustomColor`; pass `initialColor={picker.initialColor}` and `initialAlpha={picker.initialAlpha}`, as `ColorMarker.svelte` does.

`ColorPicker` gets the prop `triggerLabel?: string`, passed as `aria-label` to `Popover.Trigger`. The legend passes `triggerLabel={`Change the color of ${labelName}`}`.

- [ ] **Step 1: Write the failing test** `'keeps full opacity when Apply is clicked without changes'`: open the picker, click `Apply` → `useCustomLabelColors().getCustomColor('cat')?.alpha === 1`; `'names the picker button after the class'`: `getByRole('button', { name: 'Change the color of cat' })` exists. In `color-picker.test.ts`: `'sets the trigger aria-label from triggerLabel'`.
- [ ] **Step 2: Run** `npx vitest run src/lib/components/AnnotationColorLegend`. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Verify** the suite passes. Commit on request.

## PR 5: Extract the custom color store into a factory

**Purpose:** No behavior change. Move the body of `useCustomLabelColors.ts` into a factory so PR 8 can make a second instance.

**Files:**
- Create: `lightly_studio_view/src/lib/hooks/createCustomColorStore/createCustomColorStore.ts`
- Modify: `lightly_studio_view/src/lib/hooks/useCustomLabelColors.ts` → `const store = createCustomColorStore(); export const useCustomLabelColors = () => ({ ...store, customLabelColorsStore: store.customColorsStore });`

**Interfaces:**
- Produces: `createCustomColorStore()` → `{ customColorsStore, colorVersion, getCustomColor, setCustomColor, hasCustomColor, deleteCustomColor, clearCustomColors }`, same semantics as today. `CustomColor` moves to the factory module and is re-exported from `useCustomLabelColors.ts`.

- [ ] **Step 1: Move the code.** Existing tests (`getColorByLabel.test.ts`, `useColorPicker.test.ts`, `AnnotationColorLegend.test.ts`) cover it.
- [ ] **Step 2: Verify** `make static-checks && make test` pass with no test changes. Commit on request.

## PR 6: Keep color previews in a separate layer

**Purpose:** Today `useColorPicker` writes previews into the saved map and restores a remembered value on Cancel; any other write during a preview corrupts that value. Move previews into their own layer, owned by one picker session.

**Files:**
- Modify: `createCustomColorStore.ts`; Create: `createCustomColorStore.test.ts`
- Modify: `lightly_studio_view/src/lib/hooks/useColorPicker/useColorPicker.svelte.ts`, `useColorPicker.test.ts`

**Interfaces:**
- Factory adds:
  - `customColorsStore` becomes the saved layer overlaid with previews. A `null` preview hides the saved entry ("show the default").
  - `setPreviewColor(name: string, color: CustomColor | null, owner: symbol): void` — replaces any preview for `name`.
  - `clearPreviewColor(name: string, owner: symbol): void` — no-op unless `owner` still owns the preview.
  - `hasSavedColor(name: string): boolean` — saved layer only.
  - `replaceSavedColors(colors: Record<string, CustomColor>): void` — keeps previews.
  - `setCustomColor`/`deleteCustomColor` write the saved layer; `getCustomColor`/`hasCustomColor` read the overlaid view.
- `useColorPicker`: a session starts at the first `setColor` after a finished one, with `owner = Symbol()` and `name = getLabel()`. All preview, save and cleanup calls of the session use that `name`, not the current `getLabel()`, because a rename can change the label while the picker stays mounted (Settings rows are keyed by class ID). `setColor` → `setPreviewColor`. `finishColorChange(true)` writes the preview to the saved layer, then `clearPreviewColor`; `finishColorChange(false)` only `clearPreviewColor`. `onDestroy` also calls `clearPreviewColor` for an open session, so unmounting mid-preview (closing the settings dialog, filtering the row away) drops the preview. Remove `colorBeforePreview` and `isPreviewing`.

- [ ] **Step 1: Write failing tests.** Factory: `'a preview overrides the saved color'`, `'a null preview shows the default'`, `'clearPreviewColor of a stale owner keeps the newer preview'`, `'replaceSavedColors keeps previews'`, `'hasSavedColor ignores previews'`. Hook: `'cancel keeps a saved color written during the preview'` (preview `#abcdef`, `setCustomColor('cat', '#112233')` from outside, cancel → `#112233`); `'unmounting during a preview drops the preview'` (preview `#abcdef`, unmount the wrapper → `getCustomColor('cat')` undefined); `'cancel after a rename drops the preview of the old name'` (preview `cat`, change the label to `kitty`, cancel → `getCustomColor('cat')` undefined).
- [ ] **Step 2: Run** `npx vitest run src/lib/hooks`. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Verify** `make static-checks && make test` pass. If the partial `useCustomLabelColors` mocks in `LabelsMenu.test.ts` or `SampleDetailsClassificationSegment.test.ts` fail, add `setPreviewColor`/`clearPreviewColor: vi.fn()`. Commit on request.

**Deviations (implemented):**
- `clearCustomColors` also clears previews, so tests and a later dataset reset start clean.
- Added `getSavedColor(name)` (saved layer only); `hasSavedColor` uses it. `renameClass` in `useAnnotationClasses` reads `getSavedColor`, so a rename while a preview is open does not save the preview (Codex review).
- `useColorPickerTestWrapper.test.svelte` got a Cancel button for the new hook tests.

## PR 7: Color annotations by source through getColorBySource

**Purpose:** Readers that color by source say so. The source store is still an alias of the class store, so behavior does not change; PR 8 splits them.

Only these color by source: `SampleAnnotation`, `SampleAnnotations` + `AnnotationCanvas`, `SampleClassificationPills`. All other `getColorByLabel` callers stay (`SampleDetailsImageContainer`, `AnnotationItem`, point cloud `useWorkspaceSceneData`, `videoEvents`, `useVideoFrameAnnotations`, `plotColorUtils`).

**Files:**
- Create: `lightly_studio_view/src/lib/hooks/useCustomSourceColors/useCustomSourceColors.ts` — returns `useCustomLabelColors()` plus `customSourceColorsStore` as an alias. Comment: `// Shares the class color store until source colors get their own store.`
- Create: `lightly_studio_view/src/lib/utils/getColorBySource.ts`; Modify `getColorByLabel.ts` to extract and export `getDefaultColor`. Export from `lib/utils/index.ts` and `lib/hooks/index.ts`.
- Modify: `lightly_studio_view/src/lib/components/SampleAnnotation/SampleAnnotation.svelte` — replace `colorLabel` with `colorSource: string | undefined`; when set, stroke/fill/text/mask alpha use the source store and `getColorBySource`.
- Modify: `SampleAnnotations/index.svelte`, `AnnotationCanvas/AnnotationCanvas.svelte` — add `colorBySource?: boolean` to the canvas annotation type; `SampleAnnotations` sets it when it swaps in the source name; `resolveLabelColor` picks store and function by the flag; the canvas also re-renders on `$customSourceColorsStore`.
- Modify: `SampleClassificationPills/getSampleClassificationPills.ts` (add `colorBySource: boolean` to `SampleClassificationPill`) and `SampleClassificationPills.svelte` (`getPillColor` picks store and function by `pill.colorBySource`, keyed by `pill.colorKey`).

**Interfaces:**
- Produces: `getColorBySource(sourceName: string, alpha = 1): ColorPair`, `getDefaultColor(name: string, alpha: number): ColorPair`, `useCustomSourceColors()` (same API as `useCustomLabelColors()` plus `customSourceColorsStore`).

- [ ] **Step 1: Write failing tests:** `getColorBySource.test.ts` (`'uses a custom source color'`, `'falls back to getDefaultColor'`); `SampleAnnotations/index.test.ts` spies on `getColorBySource` for source names and expects no call in the enforce-class case; `SampleAnnotation.test.ts` source color comes from `getColorBySource('Predictions', 1)`; `getSampleClassificationPills.test.ts` expects `colorBySource`; a pill test checks that a source pill uses the color for `colorKey`.
- [ ] **Step 2: Run** them. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Verify** `make static-checks && make test` pass. Commit on request.

**Deviations (implemented):**
- `AnnotationCanvas` passes one `CustomColorMaps` object (`{ label, source }`) down the render path, and `resolveNamedColor` picks the map by the flag. This keeps the call sites short.
- Source pills look up custom colors by `pill.colorKey`. Visible change: a source pill whose class has a custom color now shows the source color, not the class color.
- `lib/utils/getColorBySource.ts` imports `useCustomSourceColors` by its deep path; the `$lib/hooks` barrel would be a circular import. Other callers use the barrel.
- The enforce-class test in `SampleAnnotations/index.test.ts` asserts the rendered stroke colors instead of a `getColorBySource` spy (Codex review).
- Size: ~227 changed lines instead of ~145, ~70 of them tests.

## PR 8: Keep annotation source colors in their own store

**Files:**
- Modify: `lightly_studio_view/src/lib/hooks/useCustomSourceColors/useCustomSourceColors.ts` — its own `createCustomColorStore()`; remove the PR 7 comment.
- Modify: `useColorPicker.svelte.ts`, `useColorPickerTestWrapper.test.svelte`, `useColorPicker.test.ts`, `AnnotationColorLegend.svelte` (`useClassColorPicker`), `SideMenu/ColorMarker/ColorMarker.svelte` + `ColorMarker.test.ts` (`useSourceColorPicker`), `hooks/index.ts`.

**Interfaces:**
- Produces: `useClassColorPicker(getName: () => string)` (`useCustomLabelColors` + `getColorByLabel`) and `useSourceColorPicker(getName: () => string)` (`useCustomSourceColors` + `getColorBySource`), replacing `useColorPicker`. Both call the private `createColorPicker(getName, colorStore, getDefaultColor)`, which has no class/source branch.

- [ ] **Step 1: Write failing tests:** `ColorMarker.test.ts` `'a source color does not change the class color with the same name'` (class `Predictions` = `#111111`, Apply `#0000ff` in `ColorMarker` → class store keeps `#111111`, source store has `#0000ff`; switch existing assertions to `useCustomSourceColors()`, and move the `getColorByLabel` spies and mocks to `getColorBySource`); `SampleAnnotation.test.ts` `'a class color does not recolor the source in source mode'`.
- [ ] **Step 2: Run** them. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Verify** `make static-checks && make test` pass. Commit on request.

**Deviations (implemented):**
- Two hooks instead of a `kind` flag: each caller knows its kind statically (review).
- `createColorPicker` reads `customColorsStore`. The partial `useCustomLabelColors` mocks in `LabelsMenu.test.ts` and `SampleDetailsClassificationSegment.test.ts` add it.
- The `customLabelColorsStore` / `customSourceColorsStore` aliases stay: they name the store at call sites, and files that use both stores would have to rename on destructure.

## PR 8b: Pass the source name to AnnotationCanvas in its own field

**Purpose:** Before this stack, `SampleAnnotations` overwrote `annotation_label_name` with the source name; PR 7 added `colorBySource` so the canvas knows how to read it. The field meant two things. Now the canvas gets the source name in its own field. No behavior change.

**Files:**
- Modify: `lightly_studio_view/src/lib/components/AnnotationCanvas/AnnotationCanvas.svelte` — in both annotation interfaces replace `colorBySource?: boolean` with `sourceName?: string` (comment: if set, color by this source instead of by class). `resolveAnnotationColor` colors by `sourceName` with the source map and `getColorBySource` when set, else by `annotation_label_name` with the label map and `getColorByLabel`. `resolveNamedColor` takes the default color function instead of a boolean.
- Modify: `SampleAnnotations/index.svelte` — set `sourceName: collectionName`; keep `annotation_label_name` as the class name.
- Modify: `AnnotationCanvas.test.ts` — the mocked 2D context reads back its last `fillStyle` (it returned a fixed color before, so no color test could fail); new test `'colors an annotation by its source name when set'`.

Out of scope: the `colorBySource` props on `SampleAnnotation`, `SampleDetailsAnnotation` and others (the name predates this stack). `AnnotationItem.svelte` never colors by source and stays unchanged.

- [x] **Step 1: Write failing test.** Failed: stroke had the class color.
- [x] **Step 2: Implement.**
- [x] **Step 3: Verify** `make static-checks && make test` pass.

## PR 9: Add "Reset to default" to the color picker

**Status:** Off the stack, under discussion (#3092, based on `main`). PRs 10–12 were rebuilt without it. If it lands after them, it also adds `resetColor` through `onCommit` (widen it to `CustomColor | undefined`, deleting on `undefined`), clearing in `saveClassColor` (`null` body), and their tests.

**Files:**
- Modify: `lightly_studio_view/src/lib/components/ui/color-picker/color-picker-panel.svelte`, `color-picker-panel.test.ts`
- Modify: `color-picker-state.svelte.ts`, `color-picker.svelte`, `color-picker.test.ts`
- Modify: `useColorPicker.svelte.ts`, `useColorPickerTestWrapper.test.svelte`, `useColorPicker.test.ts`
- Modify: `AnnotationColorLegend.svelte` — passes `onReset={picker.hasCustomColor ? picker.resetColor : undefined}`. `ColorMarker.svelte` does not pass it.
- Modify mocks: `LabelsMenu.test.ts`, `SampleDetailsClassificationSegment.test.ts` add `hasSavedColor: () => false` (read during render).
- Modify: `CHANGELOG.md` `### Added`: `- Reset an annotation class color to the default color in the color picker.`

**Interfaces:**
- `ColorPickerPanel` `Props` gets `onReset?: () => void`. When set, a `Button` (`variant="ghost"`, same size classes as Cancel, left side of the actions row, `class="mr-auto"`) shows `Reset to default`.
- `createColorPickerState` `Options` gets `getOnReset: () => (() => void) | undefined` and returns `resetToDefault(): void`: `cancelScheduledPreview()`, `hasPreviewed = false`, `isOpen = false`, then `getOnReset()?.()`. It does not call `onChange` or `onClose`.
- `ColorPicker` gets the prop `onReset?: () => void`, passes `getOnReset: () => onReset` to the state, and `onReset={onReset ? picker.resetToDefault : undefined}` to the panel.
- `createColorPicker` adds `hasCustomColor: boolean` (reactive, from `hasSavedColor`) and `resetColor(): void` (ends any open session, clearing its preview, and deletes the saved entry).

- [ ] **Step 1: Write failing tests:** panel `'shows Reset to default only when onReset is set'`; picker `'Reset to default calls onReset and closes without onClose'`; hook `'resetColor removes the custom color'` (border equals `getColorByLabel('cat', 1).color`).
- [ ] **Step 2: Run** `npx vitest run src/lib/components/ui/color-picker src/lib/hooks/useColorPicker`. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Verify** `make static-checks && make test` pass. Commit on request, with a screenshot.

## PR 10: Let the color picker save changes asynchronously

**Purpose:** Prefactor for PR 11. `applyChanges` in `color-picker-state.svelte.ts` closes the panel at once, so the user can preview again while a save is pending, and two saves can overlap.

**Files:**
- Modify: `createCustomColorStore.ts` + test
- Modify: `useColorPicker.svelte.ts`, `useColorPickerTestWrapper.test.svelte`, `useColorPicker.test.ts`

**Interfaces:**
- Factory adds:
  - `type SaveTicket = { seq: number; generation: number }`.
  - `beginSave(name: string): SaveTicket` — next save sequence for `name`, plus the current generation.
  - `setSavedColor(name: string, color: CustomColor | undefined, ticket: SaveTicket): void` — applies only if `ticket.generation` is current and `ticket.seq` is greater than the last applied for `name`; `undefined` deletes (unused until a reset exists).
  - `reset(): void` — clears the saved layer, the previews and the counters, and bumps the generation, so saves begun before it never apply. PR 12 calls it on dataset change.
  - `replaceSavedColors` keeps the counters and the generation.
  - `getGeneration(): number` — the current generation.
- `createColorPicker` gets `onCommit?: (color: CustomColor) => Promise<void>`; `useClassColorPicker(getName, options?: { onCommit? })` passes it through. `useSourceColorPicker` has no `onCommit`.
  - A session also records `getGeneration()` when it starts. If the generation changed by Apply (a dataset switch with the picker still open), Apply acts as Cancel and does not call `onCommit`.
  - `finishColorChange(applied: boolean): Promise<void>`. On Apply: capture `owner`, the preview value and `ticket = beginSave(label)`, end the session, await `onCommit?.(value)`, on success `setSavedColor(label, value, ticket)`, then always `clearPreviewColor(label, owner)`. A rejection is not rethrown; the `onCommit` owner shows the toast.
  - A `setColor` after the generation changed ends the old session and starts a new one.

- [ ] **Step 1: Write failing tests:** `'apply calls onCommit with the applied color'`, `'shows the preview until onCommit settles'`, `'reverts to the saved color when onCommit rejects'`, `'reopening while a save is pending keeps the new preview'` (Apply `#aaaaaa` with deferred `onCommit`, `setColor('#bbbbbb')`, resolve → effective `#bbbbbb`, saved `#aaaaaa`), `'an older save that resolves late does not overwrite a newer one'` (Apply A, Apply B, resolve B then A → saved B), `'apply after a store reset acts as cancel'` (preview, `reset()`, Apply → `onCommit` not called), `'a color picked after a store reset starts a new session'`; factory `'setSavedColor ignores an older sequence'`, `'reset clears saved colors and previews'`, `'setSavedColor ignores a save begun before reset'`.
- [ ] **Step 2: Run** them. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Verify** `make static-checks && make test` pass. Commit on request.

## PR 11: Save annotation class colors in the dataset

**Purpose:** Apply in the class legend saves to the server. Colors stay in the local saved layer as before; loading comes in PR 12.

**Files:**
- Modify: `lightly_studio_view/src/lib/hooks/useCustomLabelColors.ts` (name→ID map); Create `useCustomLabelColors.test.ts`.
- Modify: `lightly_studio_view/src/routes/datasets/[dataset_id]/[collection_type]/[collection_id]/+layout.svelte`, next to `annotationLabelsQuery`, two effects in this order: `$effect(() => resetAnnotationClasses(collection.dataset_id));` and `$effect(() => { if (annotationLabelsData) setAnnotationClasses(collection.dataset_id, annotationLabelsData); });`. Use `collection.dataset_id`, not the route's `datasetId`: the route param is the root collection ID, while `annotation_label.dataset_id` points to the `dataset` table. The reset runs as soon as the dataset changes, because `annotationLabelsData` is `undefined` while the new class list loads.
- Create: `lightly_studio_view/src/lib/hooks/useSaveAnnotationClassColor/useSaveAnnotationClassColor.svelte.ts` + `.svelte.test.ts`; export from `lib/hooks/index.ts`.
- Modify: `AnnotationColorLegend.svelte`: `useClassColorPicker(() => labelName, { onCommit: (color) => saveClassColor(labelName, color) })`.
- Modify: `CHANGELOG.md`: `- Annotation class colors are saved in the dataset.` (or extend the "Annotation classes" tab entry).
- Stub the save hook (`vi.mock('$lib/hooks/useSaveAnnotationClassColor/useSaveAnnotationClassColor.svelte', () => ({ useSaveAnnotationClassColor: () => ({ saveClassColor: vi.fn().mockResolvedValue(undefined) }) }))`) in every suite that renders the legend: `AnnotationColorLegend.test.ts`, `LabelsMenu.test.ts`, `AnnotationClassRow.test.ts`, `AnnotationClassesTab.test.ts`, `SettingsDialog.test.ts`, `SampleDetailsClassificationSegment.test.ts`, `SampleDetailsSidePanelAnnotation.test.ts`, `SampleDetailsAnnotationSegment.test.ts`. Add it to any other suite that fails with "No QueryClient set".

**Interfaces:**
- Consumes: `setAnnotationLabelColorMutation` (PR 3), `onCommit` (PR 10).
- Produces:
  - `resetAnnotationClasses(datasetId: string): void` — no-op if `datasetId` is the current one; otherwise records it and clears the name→ID map (PR 12 extends it).
  - `setAnnotationClasses(datasetId: string, classes: Pick<AnnotationLabelTable, 'annotation_label_id' | 'annotation_label_name' | 'dataset_id' | 'color' | 'alpha'>[]): void` — ignored unless `datasetId` is the current one; replaces the name→ID map with the classes whose `dataset_id` equals `datasetId` (PR 12 extends it).
  - `getAnnotationClassId(name: string): string | undefined`
  - `useSaveAnnotationClassColor(): { saveClassColor: (name: string, color: CustomColor) => Promise<void> }`. Unknown name: `toast.error('Could not save the annotation class color.')` and throw. Otherwise `mutateAsync({ path: { label_id }, body: { color: color.color, alpha: color.alpha } })`; `onError` shows the same toast; `onSettled` invalidates queries whose `(q.queryKey[0] as { _id?: string })?._id` is `'readAnnotationLabels'` or `'readAnnotationLabelsWithCounts'`. Saves of the same class ID run one at a time: each chains on the previous save's promise for that ID (module-level `Map<string, Promise<unknown>>`), so the server stores the last applied color.

- [ ] **Step 1: Write failing tests** (mock `@tanstack/svelte-query` as in `useAnnotationClasses.svelte.test.ts`): `'saves the color for the class ID'`, `'rejects and toasts for an unknown class'`, `'invalidates only the class list queries'`, `'sends a second save of the same class only after the first settles'`; `useCustomLabelColors.test.ts`: `'setAnnotationClasses maps names to IDs'`, `'resetAnnotationClasses to another dataset clears the class IDs'`, `'setAnnotationClasses ignores classes of another dataset'`.
- [ ] **Step 2: Run** them. Expected: FAIL.
- [ ] **Step 3: Implement** and add the stubs.
- [ ] **Step 4: Verify** `make static-checks && make test` pass. Commit on request.

## PR 12: Load annotation class colors from the dataset

**Purpose:** Colors survive a reload and show for all users. The server keys colors by class ID, so the rename workaround goes away.

**Files:**
- Modify: `useCustomLabelColors.ts` + test
- Modify: `lightly_studio_view/src/lib/components/Settings/AnnotationClassesTab/useAnnotationClasses/useAnnotationClasses.svelte.ts` + test — remove the color move in `renameClass` and the `useCustomLabelColors` mock; `renameClass` becomes `(labelId: string, name: string)`. In the test, remove the three color tests (`'renameClass moves the custom color to the new name'`, `'... keeps the custom color when the name is unchanged'`, `'... keeps colors when the rename fails'`), add `'renameClass rejects when the rename fails'`, and update the call in `'renameClass refreshes all queries'` to two arguments.
- Modify: `AnnotationClassesTab/AnnotationClassList/AnnotationClassList.svelte` — `onRename` drops `oldName`.
- Modify: `CHANGELOG.md` — the PR 11 entry now says colors are shared by all users of the dataset.

**Interfaces:**
- Consumes: `reset()` (PR 10).
- `resetAnnotationClasses(datasetId)` also calls the class store's `reset()` when the dataset changes.
- `setAnnotationClasses(datasetId, classes)` also builds one map `{ [name]: { color, alpha: alpha ?? 1 } }` from all accepted classes with a non-null `color` and calls `replaceSavedColors` once with it. It also calls it when the map is empty, so old colors go away.

- [ ] **Step 1: Write failing tests:** `'loads saved colors'` (`cat` and `bird` have colors, `dog` with null has none → both `cat` and `bird` keep their colors); `'a reload without colors clears the saved colors'` (load `cat` with a color, reload `cat` with null → none); `'replaces the previous classes'` (load `cat`, then `kitty` with the same ID → `cat` none, `kitty` has it); `'a refetch of the same dataset keeps an open preview'` (preview `cat` = `#abcdef`, reload `ds-1` with saved `#112233` → `#abcdef`); `'switching datasets drops previews and colors'` (load and preview `cat` in `ds-1`, `resetAnnotationClasses('ds-2')` → `getCustomColor('cat')` undefined before any `ds-2` classes load).
- [ ] **Step 2: Run** them. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Verify** `make static-checks && make test` pass.
- [ ] **Step 5: Manual check** with `cd lightly_studio && make build-lightly_studio_view` and a fresh DuckDB file: set a class color and reload (kept); rename (kept); add a class with a legend picker open (preview stays); switch dataset with a picker open (nothing carries over); set a source color (class color unchanged). Commit on request.
