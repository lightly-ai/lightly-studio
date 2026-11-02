# Annotation Class Colors in the DB Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Save custom annotation class colors per dataset in the database, so all users of a dataset see them after a reload, and add "Reset to default" to the color picker.

**Architecture:** Nullable `color`/`alpha` columns on `annotation_label` and a `PUT /annotation_labels/{label_id}/color` endpoint. In the frontend, class colors and source colors live in two separate stores made by one factory. Class lookups use `getColorByLabel`, source lookups use the new `getColorBySource`. Each store has a saved layer and a local preview layer. Apply saves the preview, Cancel discards it, and a class-list refetch replaces only the saved layer.

**Tech Stack:** FastAPI, SQLModel, Alembic (PostgreSQL), DuckDB (`create_all`), SvelteKit, Svelte 5, TanStack Query, hey-api generated client, vitest, pytest.

**Spec:** `.experimental/superpowers/specs/2026-11-02-annotation-class-colors-in-db-design.md`

## Global Constraints

- Colors are per dataset, not per user.
- `color`/`alpha` are nullable. Null means the default (hashed palette) color.
- A rename must not clear the color. `PUT /annotation_labels/{label_id}` keeps taking `AnnotationLabelCreate`; do not add color fields to `AnnotationLabelBase`/`AnnotationLabelCreate`.
- Class and source colors never share a map. A call site that colors by source calls `getColorBySource` and reads the source store; every other call site uses `getColorByLabel` and the class store. There is no tie-break.
- Live preview is a local layer. Apply saves it, Cancel discards it, a refetch does not drop it. On save error: toast and revert to the saved color.
- Source colors stay browser-only. Out of scope: live updates from other users, export/import of colors.
- Existing DuckDB files are not upgraded (as in #2782). PR 1 adds a CHANGELOG note.
- User-facing text uses "annotation class" and "annotation source" (glossary), never "label".
- Skills to load before editing: `python-guide` + `backend-guide` for `lightly_studio/**`; `frontend-guide` for `lightly_studio_view/**`; `best-practices` for new modules; `changelog` for `CHANGELOG.md`; `pull-requests` before opening each PR.
- Each PR stays under ~200 changed lines, excluding `lightly_studio_view/src/lib/api/**` and lockfiles. Do not commit or push unless the user asks (repo memory: ask before commit; no force push).
- Validation. Backend: `cd lightly_studio && make static-checks && uv run pytest <tests>`; for the migration also `make migration-check-postgresql`. Frontend: `cd lightly_studio_view && make static-checks && make test` (Node from `.nvmrc`).

## Review Focus

1. **Class list refetch while a class picker is open.** The preview stays on screen, and Apply saves the preview, not the refetched value. Test: PR 7 Task 7.1.
2. **A source and a class with the same name** (e.g. both `"Predictions"`). Setting one does not change how the other renders, in both color modes. Tests: PR 5 Tasks 5.1 and 5.3.
3. **Save or reset fails** (network error, class deleted meanwhile, class not in the loaded list). A toast shows and the swatch goes back to the saved color. Tests: PR 6 Task 6.2, PR 7 Task 7.2.
4. **Rename a class, or switch to another dataset.** The color follows the class ID, and colors of the previous dataset do not stay. Tests: PR 1 Task 1.2, PR 7 Task 7.1.
5. **Apply without touching the opacity slider.** The stored alpha is 1, not 0.4. Test: PR 3. Also, a color without an alpha returns 422 (PR 2).

---

## PR stack

| # | Title | Base | Est. LOC (excl. generated) |
|---|-------|------|----------------------------|
| 1 | Add color columns to annotation classes | `michal-lig-11319-annotation-classes-tab-ui` | ~155 |
| 2 | Add an endpoint to set an annotation class color | PR 1 | ~95 (+ generated client) |
| 3 | Seed the annotation class color picker from useColorPicker | PR 2 (no code dependency) | ~45 |
| 4 | Keep color previews in a separate layer | PR 3 | ~130 |
| 5 | Color annotation sources from their own color store | PR 4 | ~180 |
| 6 | Add "Reset to default" to the color picker | PR 5 | ~130 |
| 7 | Save annotation class colors in the dataset | PR 6 | ~190 |

PRs 1–2 are backend only. PRs 3–6 are frontend prefactors that ship on their own: a bug fix, an internal refactor, a fix for class/source collisions, and a local reset. PR 7 turns on persistence and removes the rename workaround.

---

## PR 1: Add color columns to annotation classes

**Purpose:** Store a nullable color per annotation class and return it from the class list endpoints. There is no way to set it over HTTP yet.

### Task 1.1: Columns, view fields, migration, CHANGELOG

**Files:**
- Modify: `lightly_studio/src/lightly_studio/models/annotation_label.py`
- Modify: `lightly_studio/src/lightly_studio/api/routes/api/annotation_label.py` (`read_annotation_labels_with_counts`)
- Create: `lightly_studio/src/lightly_studio/migrations/versions/<generated>_add_annotation_label_color.py`
- Modify: `CHANGELOG.md`
- Test: `lightly_studio/tests/api/routes/api/test_annotation_label.py`

**Interfaces:**
- Produces: `AnnotationLabelTable.color: str | None = None` and `AnnotationLabelTable.alpha: float | None = None`. The same two fields go on `AnnotationLabelView`, so `AnnotationLabelWithCountView` has them too. They do not go on Base or Create.

- [ ] **Step 1: Write the failing test** `test_get_annotation_labels__color`. Create a label, set `color = "#ff8040"` and `alpha = 0.5`, and commit. Both `GET /api/collections/{id}/annotation_labels_with_counts` and `GET /api/collections/{id}/annotation_labels` return these values. A label without a color returns `color is None` and `alpha is None`.
- [ ] **Step 2: Run** `cd lightly_studio && uv run pytest tests/api/routes/api/test_annotation_label.py -k color`. Expected: FAIL.
- [ ] **Step 3: Add the fields.** Table comment: `# Custom display color as "#rrggbb", and its opacity in [0, 1]. Null means the default color.` In `read_annotation_labels_with_counts`, pass `color=label.color, alpha=label.alpha`.
- [ ] **Step 4: Generate the migration.** Run `make start-postgres && make migration-revision-postgresql MSG=add_annotation_label_color`. `down_revision` must be the current head: today `b7d24e8f913a`, but run `uv run alembic heads` after merging main. Keep only two `op.add_column("annotation_label", ...)` calls: `color` (`AutoString()`, nullable) and `alpha` (`sa.Float()`, nullable). `downgrade` drops both. Follow the style of `1791936000_8cb37a9d104e_add_image_interpolation_setting.py`.
- [ ] **Step 5: Add the CHANGELOG entry** under `## [Unreleased]` → `### Changed`, following the `changelog` skill and the wording of the existing DuckDB entry: `- BREAKING: DuckDB databases created before this version are not upgraded and fail to open. Re-index your data.`
- [ ] **Step 6: Verify** that the test passes, `make migration-check-postgresql` passes, and `make static-checks` passes.

### Task 1.2: `set_color` resolver

**Files:**
- Create: `lightly_studio/src/lightly_studio/resolvers/annotation_label_resolver/set_color.py`
- Modify: `lightly_studio/src/lightly_studio/resolvers/annotation_label_resolver/__init__.py` (export `set_color`)
- Test: `lightly_studio/tests/resolvers/annotation_label_resolver/test_set_color.py`, `test_update.py`, `lightly_studio/tests/resolvers/dataset_resolver/test_deep_copy.py`

**Interfaces:**
- Produces: `annotation_label_resolver.set_color(session: Session, label_id: UUID, color: str | None, alpha: float | None) -> AnnotationLabelTable | None`. It returns `None` for an unknown label. It sets both fields, commits and refreshes. Validation lives in the request model (PR 2).

- [ ] **Step 1: Write failing tests:**
  - `test_set_color`: setting `"#ff8040"` and `0.5` → the returned label and a re-read label both have them.
  - `test_set_color__clear`: set a color, then `color=None, alpha=None` → both fields are `None`.
  - `test_set_color__unknown_label` → returns `None`.
  - `test_update__keeps_color` in `test_update.py`: set a color, rename with `update` → the name changes and the color and alpha stay.
  - `test_deep_copy__annotation_label_color` in `test_deep_copy.py`: the copied label has the same `color`/`alpha`. `_copy_table` copies every column it does not remap; this test makes sure that stays true.
- [ ] **Step 2: Run** `uv run pytest tests/resolvers/annotation_label_resolver tests/resolvers/dataset_resolver/test_deep_copy.py -k color`. Expected: the `test_set_color*` tests FAIL.
- [ ] **Step 3: Implement `set_color`** following `update.py`.
- [ ] **Step 4: Run** the same command and expect PASS. Then run `make static-checks`.
- [ ] **Step 5: Commit** (only when the user asks).

---

## PR 2: Add an endpoint to set an annotation class color

**Purpose:** `PUT /api/annotation_labels/{label_id}/color` sets or clears the color. This PR regenerates the frontend client.

### Task 2.1: Route and request model

**Files:**
- Modify: `lightly_studio/src/lightly_studio/api/routes/api/annotation_label.py`
- Test: `lightly_studio/tests/api/routes/api/test_annotation_label.py`
- Generated: `lightly_studio_view/src/lib/api/lightly_studio_local/**`

**Interfaces:**
- Consumes: `annotation_label_resolver.set_color` (PR 1).
- Produces:
  - `class AnnotationLabelColorRequest(BaseModel)` with:
    - `color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")`
    - `alpha: float | None = Field(default=None, ge=0, le=1)`
    - a `model_validator(mode="after")` that raises `ValueError` unless both fields are set or both are `None`.
  - `set_annotation_label_color(label_id: UUID, color_input: AnnotationLabelColorRequest, session: SessionDep) -> AnnotationLabelTable` on `PUT /annotation_labels/{label_id}/color`. It raises `NotFoundError("Annotation label not found")` for an unknown label.
  - In the generated client: `setAnnotationLabelColorMutation()`, and `AnnotationLabelTable` gets `color?: string | null` and `alpha?: number | null`.

- [ ] **Step 1: Write failing tests:**
  - `test_set_annotation_label_color`: `{"color": "#FF8040", "alpha": 0.5}` → 200, and a GET returns the same values.
  - `test_set_annotation_label_color__clear`: `{"color": null, "alpha": null}` → 200, both fields `None`.
  - `test_set_annotation_label_color__invalid` → 422, parametrized over:
    - `{"color": "red", "alpha": 1}`
    - `{"color": "#ff8040", "alpha": 1.5}`
    - `{"color": "#ff8040", "alpha": null}`
    - `{"color": null, "alpha": 0.5}`
  - `test_set_annotation_label_color__not_found` → 404.
  - `test_update_annotation_label__keeps_color`: set a color with the new endpoint, then rename with `PUT /annotation_labels/{id}` → the color stays.
- [ ] **Step 2: Run** `uv run pytest tests/api/routes/api/test_annotation_label.py -k color`. Expected: FAIL.
- [ ] **Step 3: Implement** the request model and the route.
- [ ] **Step 4: Run** and expect PASS. Then run `make static-checks`.
- [ ] **Step 5: Regenerate the client** with `make export-schema`, then `npm run generate-api-client` in `lightly_studio_view`. Then run `make static-checks` in `lightly_studio_view`.
- [ ] **Step 6: Commit** (on request).

---

## PR 3: Seed the annotation class color picker from useColorPicker

**Purpose:** Prefactor and bug fix. `AnnotationColorLegend` has its own `getInitialColor`/`getInitialAlpha`, and its default alpha is 0.4. So Apply without changes stores alpha 0.4 and dims the class.

**Files:** `lightly_studio_view/src/lib/components/AnnotationColorLegend/AnnotationColorLegend.svelte` and `AnnotationColorLegend.test.ts`. Delete `getInitialColor`, `getInitialAlpha` and the destructured `getCustomColor`/`hasCustomColor`.

- [ ] **Step 1: Write the failing test** `'keeps full opacity when Apply is clicked without changes'`: open the picker, click `Apply` → `getCustomColor('cat')?.alpha === 1`.
- [ ] **Step 2: Run** `npx vitest run src/lib/components/AnnotationColorLegend`. Expected: FAIL.
- [ ] **Step 3: Pass `initialColor={picker.initialColor}` and `initialAlpha={picker.initialAlpha}`** to `ColorPicker`.
- [ ] **Step 4: Run** and expect PASS. Then run `make static-checks`. **Step 5: Commit** (on request).

---

## PR 4: Keep color previews in a separate layer

**Purpose:** Prefactor. Today `useColorPicker` writes previews into the one color map and restores a remembered value on Cancel. Anything that writes the map during a preview corrupts that value. This PR moves the store into a factory that has a saved layer and a preview layer. Behavior does not change.

### Task 4.1: `createCustomColorStore` factory

**Files:**
- Create: `lightly_studio_view/src/lib/hooks/createCustomColorStore/createCustomColorStore.ts` and `createCustomColorStore.test.ts`
- Modify: `lightly_studio_view/src/lib/hooks/useCustomLabelColors.ts`. It becomes a module-level instance of the factory. The returned API keeps its current names, so the ~10 test files that call `setCustomColor`/`clearCustomColors` do not change.

**Interfaces:**
- Produces: `createCustomColorStore()` returns:
  - `customColorsStore: Readable<Record<string, CustomColor>>`: the saved layer overlaid with the preview layer. A preview of `null` removes the entry, which means "show the default color".
  - `colorVersion: Writable<number>`: bumped on every change.
  - `getCustomColor(name): CustomColor | undefined` and `hasCustomColor(name): boolean`: read the overlaid view.
  - `hasSavedColor(name): boolean`: reads the saved layer only.
  - `setCustomColor(name, color, alpha = 1)` and `deleteCustomColor(name)`: write the saved layer.
  - `replaceSavedColors(colors: Record<string, CustomColor>)`: replaces the saved layer and leaves previews alone.
  - `setPreviewColor(name, color: CustomColor | null)` and `clearPreviewColor(name)`.
  - `clearCustomColors()`: clears both layers.
- `useCustomLabelColors()` returns this API, with `customLabelColorsStore` as an alias for `customColorsStore` so readers do not change.

- [ ] **Step 1: Write failing tests:**
  - `'a preview overrides the saved color'`
  - `'clearing a preview shows the saved color again'`
  - `'a null preview shows the default'`: `getCustomColor` is undefined while a saved color exists.
  - `'replaceSavedColors keeps an open preview'`
  - `'hasSavedColor ignores previews'`
- [ ] **Step 2: Run** `npx vitest run src/lib/hooks/createCustomColorStore`. Expected: FAIL. **Step 3: Implement** with `writable` + `derived`. **Step 4: Run** and expect PASS.

### Task 4.2: `useColorPicker` uses the preview layer

**Files:** `lightly_studio_view/src/lib/hooks/useColorPicker/useColorPicker.svelte.ts` and `useColorPicker.test.ts`

**Interfaces:**
- `setColor(color, alpha)` calls `setPreviewColor(label, { color, alpha })`.
- `finishColorChange(applied)`: when applied, write the preview to the saved layer, then clear the preview. When not applied, only clear the preview. Remove `colorBeforePreview` and `isPreviewing`.

- [ ] **Step 1: Write the failing test** `'cancel keeps a saved color written during the preview'`. Preview `#abcdef`, then call `setCustomColor('cat', '#112233')` from outside, then cancel → the color is `#112233`. The current hook restores the stale value instead.
- [ ] **Step 2: Run** and expect FAIL. **Step 3: Implement.** **Step 4: Run** `make static-checks && make test` and expect PASS. **Step 5: Commit** (on request).

---

## PR 5: Color annotation sources from their own color store

**Purpose:** A source named like a class (e.g. `"Predictions"`) currently overwrites that class's color, and the reverse. This PR adds a separate source store and `getColorBySource`. Call sites that color by source switch to them.

### Task 5.1: Source store and `getColorBySource`

**Files:**
- Create: `lightly_studio_view/src/lib/hooks/useCustomSourceColors.ts`: a second module-level instance of `createCustomColorStore`. It exports `useCustomSourceColors()`, which returns the factory API with `customSourceColorsStore` as the alias.
- Create: `lightly_studio_view/src/lib/utils/getColorBySource.ts` and `getColorBySource.test.ts`
- Modify: `lightly_studio_view/src/lib/utils/getColorByLabel.ts`. Extract `getDefaultColor(name: string, alpha: number)` (palette + hash) and export it for `getColorBySource`.
- Modify: `lightly_studio_view/src/lib/utils/index.ts` and `lightly_studio_view/src/lib/hooks/index.ts` (exports)

**Interfaces:**
- Produces:
  - `getColorBySource(sourceName: string, alpha = 1): ColorPair`. It works like `getColorByLabel`, but reads `useCustomSourceColors()`.
  - `getDefaultColor(name: string, alpha: number): ColorPair`.

- [ ] **Step 1: Write failing tests:**
  - `'uses the source color, not the class color of the same name'`: class `Predictions` = `#111111`, source `Predictions` = `#222222` → `getColorBySource('Predictions').color` is rgba of `#222222`, and `getColorByLabel('Predictions').color` is rgba of `#111111`.
  - `'falls back to the same default as getColorByLabel'`.
- [ ] **Step 2: Run** and expect FAIL. **Step 3: Implement.** **Step 4: Run** and expect PASS.

### Task 5.2: `useColorPicker` picks a store by kind

**Files:** `useColorPicker.svelte.ts`, `useColorPickerTestWrapper.test.svelte`, `AnnotationColorLegend.svelte`, `SideMenu/ColorMarker/ColorMarker.svelte`, `ColorMarker.test.ts`

**Interfaces:**
- Produces: `export type ColorKind = 'class' | 'source'` and `useColorPicker(getLabel: () => string, options: { kind: ColorKind })`.
  - `'class'` uses `useCustomLabelColors` and `getColorByLabel`; `'source'` uses `useCustomSourceColors` and `getColorBySource`.
  - The legend passes `'class'`; `ColorMarker` passes `'source'`.

- [ ] **Step 1: Write the failing test** in `ColorMarker.test.ts`: `'a source color does not change the class color with the same name'`. Set class `Predictions` = `#111111`, Apply `#0000ff` in `ColorMarker` → the class store still has `#111111` and the source store has `#0000ff`. Switch existing `ColorMarker` assertions to `useCustomSourceColors()`.
- [ ] **Step 2–4:** Run, implement, run `npx vitest run src/lib/components/SideMenu src/lib/hooks/useColorPicker`.

### Task 5.3: Call sites that color by source

Only these call sites color by source; the rest stay on `getColorByLabel`. I checked every `getColorByLabel` and `customLabelColorsStore` caller. `SampleDetailsImageContainer`, `AnnotationItem`, `PointCloud useWorkspaceSceneData`, `videoEvents`, `useVideoFrameAnnotations` and `PlotPanel/plotColorUtils` use class names or non-source names.

**Files:**
- `lightly_studio_view/src/lib/components/SampleAnnotation/SampleAnnotation.svelte`: replace `colorLabel` with `colorSource: string | undefined` (the source name when coloring by source). `colorText`, `colorStroke` and `colorFill` read `$customSourceColorsStore[colorSource]` + `getColorBySource` when `colorSource` is set, else the class store + `getColorByLabel`. Check the mask alpha read (`customColor?.alpha`) further down the file the same way.
- `lightly_studio_view/src/lib/components/SampleAnnotations/index.svelte` and `lightly_studio_view/src/lib/components/AnnotationCanvas/AnnotationCanvas.svelte`:
  - Add `colorBySource?: boolean` to the canvas annotation type, next to where `InstanceAnnotation`/`ObjectDetectionAnnotation` are declared.
  - `SampleAnnotations` sets it when it swaps in the source name.
  - In the canvas, `resolveLabelColor` takes both maps and uses the source map + `getColorBySource` when the flag is set. The canvas re-renders on changes to either store: subscribe to `$customSourceColorsStore` next to `$customLabelColorsStore` (lines ~225 and ~359).
- `lightly_studio_view/src/lib/components/SampleClassificationPills/getSampleClassificationPills.ts`: add `colorBySource: boolean` to `SampleClassificationPill`, set from `showSourceColors`.
- `lightly_studio_view/src/lib/components/SampleClassificationPills/SampleClassificationPills.svelte`: `getPillColor` reads the store and color function for `pill.colorBySource`, keyed by `pill.colorKey`. Today it reads the class map by `pill.label` even in source mode, which is a bug.

- [ ] **Step 1: Update or write failing tests:**
  - `SampleAnnotation.test.ts` (line ~186): the source color comes from `getColorBySource('Predictions', 1)`. New test: a class color for `Predictions` does not change the stroke in source mode.
  - `SampleAnnotations/index.test.ts` (lines ~309–340): spy on `getColorBySource` for source names. The enforce-class test asserts `getColorBySource` is not called.
  - `getSampleClassificationPills.test.ts`: the expected pills include `colorBySource`.
- [ ] **Step 2: Run** these suites and expect FAIL. **Step 3: Implement.** **Step 4: Run** `make static-checks && make test` and expect PASS.
- [ ] **Step 5: Manual check:** with two sources visible, pick a source color in the sidebar. Annotations, pills and the details view use it, and the class colors stay the same with "color by class" enforced. **Commit** (on request).

---

## PR 6: Add "Reset to default" to the color picker

**Purpose:** Users can drop a custom color. This PR also adds the commit hook that PR 7 uses for saving. Reset is local for both classes and sources here.

### Task 6.1: `ColorPicker` reset action

**Files:** `lightly_studio_view/src/lib/components/ui/color-picker/color-picker.svelte` and `color-picker.test.ts`

**Interfaces:**
- Produces: the prop `onReset?: () => void`. When it is set, a `Button` (`variant="ghost"`, same size classes as Cancel, left in the actions row) shows the text `Reset to default`.
- Click does: `cancelScheduledPreview()`, `onReset()`, `hasPreviewed = false`, `isOpen = false`. It does not call `onClose` or `onChange`.

- [ ] **Step 1: Write failing tests:**
  - `'shows Reset to default only when onReset is set'`
  - `'Reset to default calls onReset and closes without onClose'`
- [ ] **Step 2–4:** Run `npx vitest run src/lib/components/ui/color-picker`, implement, and run again.

### Task 6.2: `useColorPicker` reset and commit

**Files:** `useColorPicker.svelte.ts`, `useColorPickerTestWrapper.test.svelte`, `useColorPicker.test.ts`, `AnnotationColorLegend.svelte`, `ColorMarker.svelte`. Both components pass `onReset={picker.hasCustomColor ? picker.resetColor : undefined}`.

**Interfaces:**
- Produces: `useColorPicker(getLabel, options: { kind: ColorKind; onCommit?: (color: CustomColor | undefined) => Promise<void> })`. It adds:
  - `hasCustomColor: boolean`, from `hasSavedColor` of the kind's store, reactive.
  - `finishColorChange(applied: boolean): Promise<void>`. When applied, it takes the preview value and awaits `onCommit?.(value)`. On success it writes the saved layer and clears the preview. If `onCommit` rejects, it only clears the preview, which reverts to the saved color. When not applied, it clears the preview.
  - `resetColor(): Promise<void>`. It calls `setPreviewColor(label, null)` and awaits `onCommit?.(undefined)`. On success it deletes the saved entry. In all cases it then clears the preview.
- The hook does not toast. The owner of `onCommit` does (PR 7).

- [ ] **Step 1: Write failing tests:**
  - `'resetColor removes the custom color'`: the border equals `getColorByLabel('cat', 1).color`.
  - `'apply calls onCommit with the applied color'` → called with `{ color: '#abcdef', alpha: 0.5 }`.
  - `'reverts to the saved color when onCommit rejects on apply'`
  - `'keeps the saved color when onCommit rejects on reset'`
  - `'shows the preview until onCommit settles'`
- [ ] **Step 2–4:** Run, implement, then run `make static-checks && make test`.
- [ ] **Step 5:** CHANGELOG `### Added`: `- Reset a custom color to the default color in the color picker.` **Commit** (on request) with a screenshot in the PR.

---

## PR 7: Save annotation class colors in the dataset

**Purpose:** The feature. Class colors load from the class list into the saved layer and save on Apply/Reset. Renames keep colors because the server keys them by class ID. The rename workaround goes away.

### Task 7.1: Load class colors and IDs

**Files:**
- Modify: `lightly_studio_view/src/lib/hooks/useCustomLabelColors.ts` and its test (create `useCustomLabelColors.test.ts`)
- Modify: `lightly_studio_view/src/routes/datasets/[dataset_id]/[collection_type]/[collection_id]/+layout.svelte`, next to `annotationLabelsQuery` (~line 338)

**Interfaces:**
- Consumes: the generated `AnnotationLabelTable` with `color`/`alpha` (PR 2), and `replaceSavedColors` (PR 4).
- Produces, on `useCustomLabelColors()`:
  - `setAnnotationClasses(classes: Pick<AnnotationLabelTable, 'annotation_label_id' | 'annotation_label_name' | 'color' | 'alpha'>[]): void`. It calls `replaceSavedColors` with `{ [name]: { color, alpha: alpha ?? 1 } }` for every class with a non-null `color`, and replaces a name→ID map.
  - `getAnnotationClassId(name: string): string | undefined`.
- In the layout: `$effect(() => { if (annotationLabelsData) setAnnotationClasses(annotationLabelsData); });`

- [ ] **Step 1: Write failing tests:**
  - `'loads saved colors and IDs'`: `cat` gets a color, `dog` with a null color gets none, and `getAnnotationClassId('dog') === '2'`.
  - `'replaces the previous classes'`: load `cat` with a color, then load `[kitty]` with the same ID and color → `cat` has no color or ID, and `kitty` has both. This covers renames and dataset switches.
  - `'keeps an open preview'`: `setPreviewColor('cat', {...'#abcdef'})`, then `setAnnotationClasses([...cat saved '#112233'])` → `getCustomColor('cat')` is `#abcdef`. After `clearPreviewColor('cat')` it is `#112233`.
- [ ] **Step 2–4:** Run, implement the store function and the layout effect, then run again.

### Task 7.2: Save hook, legend wiring, drop the rename workaround

**Files:**
- Create: `lightly_studio_view/src/lib/hooks/useSaveAnnotationClassColor/useSaveAnnotationClassColor.svelte.ts` and `useSaveAnnotationClassColor.svelte.test.ts`. Export it from `lightly_studio_view/src/lib/hooks/index.ts`.
- Modify: `AnnotationColorLegend.svelte`: `useColorPicker(() => labelName, { kind: 'class', onCommit: (color) => saveClassColor(labelName, color) })`
- Modify: `lightly_studio_view/src/lib/components/Settings/AnnotationClassesTab/useAnnotationClasses/useAnnotationClasses.svelte.ts` and its test.
  - Remove the color move from `renameClass` and remove the `useCustomLabelColors` mock.
  - `oldName` exists only for the workaround. Remove it from `renameClass` and from `onRename` in `AnnotationClassList.svelte`, plus the caller in `AnnotationClassRow`.

**Interfaces:**
- Consumes: `setAnnotationLabelColorMutation` (PR 2), `getAnnotationClassId` (7.1), `onCommit` (PR 6).
- Produces: `useSaveAnnotationClassColor(): { saveClassColor: (name: string, color: CustomColor | undefined) => Promise<void> }`.
  - For an unknown name: `toast.error('Could not save the annotation class color.')`, then throw, so the picker reverts.
  - Otherwise: `mutateAsync({ path: { label_id }, body: { color: color?.color ?? null, alpha: color?.alpha ?? null } })`.
  - `onError`: the same toast.
  - `onSettled`: invalidate only the class-list queries. Use `client.invalidateQueries({ predicate })`, where the predicate is true when `(q.queryKey[0] as { _id?: string })?._id` is `'readAnnotationLabels'` or `'readAnnotationLabelsWithCounts'`.

- [ ] **Step 1: Write failing tests.** Mock `@tanstack/svelte-query` as in `useAnnotationClasses.svelte.test.ts`.
  - `'saves the color for the class ID'`
  - `'clears the color on reset'` → the body is `{ color: null, alpha: null }`.
  - `'rejects and toasts for an unknown class'`
  - `'rejects and toasts when the request fails'`
  - `'invalidates only the class list queries'`
- [ ] **Step 2: Run** `npx vitest run src/lib/hooks/useSaveAnnotationClassColor`. Expected: FAIL.
- [ ] **Step 3: Implement.** Wire the legend and remove the workaround, together with its test `'renameClass moves the custom color to the new name'`.
- [ ] **Step 4: Run** `make static-checks && make test` and expect PASS.
- [ ] **Step 5: Manual check.** Run `cd lightly_studio && make build-lightly_studio_view` once, use a fresh DuckDB file, then check:
  - Set a class color, reload → the color is kept.
  - Rename the class in Settings → the color is kept.
  - Reset to default → the default color shows after a reload.
  - Add a class while a legend picker is open → the preview stays.
  - Set a source color → the class color does not change.
- [ ] **Step 6: CHANGELOG** `### Added`: `- Annotation class colors are saved in the dataset and shared by all its users.` **Commit** (on request).

---

## Open questions

1. **Non-class names in `getColorByLabel`.** `PlotPanel/plotColorUtils` colors plot categories (for example tag names like `"Train"`) with `getColorByLabel`. A class with the same name and a saved color would then recolor that plot category. This happens today too. Keep it, or move plots to `getDefaultColor`?
2. **Size of PR 5.** It touches the most call sites (~180 lines with tests). If review wants it smaller, split it: Tasks 5.1+5.2 (store, `getColorBySource`, picker) as one PR, Task 5.3 (renderers) as the next. The catch: between the two PRs, source colors set in the sidebar would not show in annotations, so the two would have to merge together.
