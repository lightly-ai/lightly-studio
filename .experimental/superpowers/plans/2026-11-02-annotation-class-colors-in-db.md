# Annotation Class Colors in the DB Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Save custom annotation class colors per dataset in the database, so all users of a dataset see them after a reload, and add "Reset to default" to the color picker.

**Architecture:** Nullable `color`/`alpha` columns on `annotation_label` and a `PUT /annotation_labels/{label_id}/color` endpoint. In the frontend, one factory makes two color stores: one for class colors, one for source colors. Class lookups use `getColorByLabel`; source lookups use the new `getColorBySource`. Each store has a saved layer and a local preview layer. A preview belongs to the picker session that started it. Apply saves the preview and Cancel discards it. A class-list refetch replaces only the saved layer, and a dataset change also clears the previews.

**Tech Stack:** FastAPI, SQLModel, Alembic (PostgreSQL), DuckDB (`create_all`), SvelteKit, Svelte 5, TanStack Query, hey-api generated client, vitest, pytest.

**Spec:** `.experimental/superpowers/specs/2026-11-02-annotation-class-colors-in-db-design.md`

## Global Constraints

- Colors are per dataset, not per user.
- `color`/`alpha` are nullable. Null means the default (hashed palette) color.
- A rename must not clear the color. `PUT /annotation_labels/{label_id}` keeps taking `AnnotationLabelCreate`; do not add color fields to `AnnotationLabelBase` or `AnnotationLabelCreate`.
- Class colors and source colors never share a map. A call site that colors by source uses `getColorBySource` and the source store; every other call site uses `getColorByLabel` and the class store.
- Live preview is a local layer. Apply saves it, Cancel discards it, a same-dataset refetch keeps it, a dataset change clears it. If a save fails, show a toast and revert to the saved color. A slow save never clears a newer preview, and an older save never overwrites a newer one.
- Source colors stay browser-only. Out of scope: live updates from other users, export/import of colors.
- Existing DuckDB files are not upgraded (as in #2782). PR 1 adds a CHANGELOG note.
- User-facing text says "annotation class" and "annotation source" (glossary), never "label".
- Skills to load before editing: `python-guide` + `backend-guide` for `lightly_studio/**`; `frontend-guide` for `lightly_studio_view/**`; `best-practices` for new modules; `changelog` for `CHANGELOG.md`; `pull-requests` before opening each PR.
- Frontend tests run without a `QueryClientProvider`. The convention is to stub hooks that use TanStack (see `VideoDetails.test.ts:52`).
- Each PR stays under ~200 changed lines (additions + deletions, tests and mock updates included). This excludes `lightly_studio_view/src/lib/api/**` and lockfiles. Do not commit or push unless the user asks (repo memory: ask before commit; no force push).
- Validation:
  - Backend: `cd lightly_studio && make static-checks && uv run pytest <tests>`. Migration PRs also run `make migration-check-postgresql`.
  - Frontend: `cd lightly_studio_view && make static-checks && make test` (Node from `.nvmrc`).

## Review Focus

1. **Class list refetch while a class picker is open.** The preview stays and Apply saves it. Test: PR 12.
2. **Reopen the picker while a save is pending, or apply twice quickly.**
   - The first save does not clear the second preview.
   - An older save that resolves late does not overwrite the newer saved color.
   - Test: PR 10.
3. **Switch to another dataset while a preview is open or a save is pending.** No color of the old dataset shows in the new one. Test: PR 12.
4. **A source and a class with the same name** (e.g. `"Predictions"`). Changing one never changes the other. Tests: PRs 7 and 8.
5. **Save or reset fails** (network error, class deleted meanwhile, class missing from the loaded list). A toast shows, and the swatch shows the saved color. Tests: PRs 10 and 11.

---

## PR stack

LOC = additions + deletions, tests and mock updates included, generated files excluded.

| # | Title | Base | Est. LOC |
|---|-------|------|----------|
| 1 | Add color columns to annotation classes | `michal-lig-11319-annotation-classes-tab-ui` | ~90 |
| 2 | Add a resolver to set an annotation class color | PR 1 | ~115 |
| 3 | Add an endpoint to set an annotation class color | PR 2 | ~110 (+ generated client) |
| 4 | Seed the annotation class color picker from useColorPicker | PR 3 (no code dependency) | ~45 |
| 5 | Extract the custom color store into a factory | PR 4 | ~130 (mostly moved code) |
| 6 | Keep color previews in a separate layer | PR 5 | ~170 |
| 7 | Color annotations by source through getColorBySource | PR 6 | ~145 |
| 8 | Keep annotation source colors in their own store | PR 7 | ~110 |
| 9 | Add "Reset to default" to the color picker | PR 8 | ~115 |
| 10 | Let the color picker save changes asynchronously | PR 9 | ~140 |
| 11 | Save annotation class colors in the dataset | PR 10 | ~195 |
| 12 | Load annotation class colors from the dataset | PR 11 | ~125 |

Each PR is mergeable on its own:

- **PRs 1–3** are backend only.
- **PRs 4–10** are frontend prefactors with no broken intermediate state:
  - PR 4 is a bug fix.
  - PRs 5–6 are refactors.
  - PR 7 switches the readers while the source store is still an alias of the class store.
  - PR 8 splits the stores.
  - PR 9 adds a local reset.
  - PR 10 adds an async commit option with tests; PR 11 is its first user.
- **PR 11** saves first. Session colors persist to the server and stay in the local saved layer.
- **PR 12** loads. It must come after PR 11, because loading without saving would wipe session colors on every refetch.

---

## PR 1: Add color columns to annotation classes (~90)

**Files:**
- Modify: `lightly_studio/src/lightly_studio/models/annotation_label.py`
- Modify: `lightly_studio/src/lightly_studio/api/routes/api/annotation_label.py` (`read_annotation_labels_with_counts`)
- Create: `lightly_studio/src/lightly_studio/migrations/versions/<generated>_add_annotation_label_color.py`
- Modify: `CHANGELOG.md`
- Test: `lightly_studio/tests/api/routes/api/test_annotation_label.py`, `lightly_studio/tests/resolvers/dataset_resolver/test_deep_copy.py`

**Interfaces:**
- Produces: `AnnotationLabelTable.color: str | None = None` and `AnnotationLabelTable.alpha: float | None = None`. The same two fields go on `AnnotationLabelView`, so `AnnotationLabelWithCountView` has them too. They do not go on Base or Create.

- [ ] **Step 1: Write failing tests:**
  - `test_get_annotation_labels__color`: set `color = "#ff8040"` and `alpha = 0.5` directly on a label and commit. Both `GET .../annotation_labels` and `GET .../annotation_labels_with_counts` return these values. A label without a color returns `None` for both fields.
  - `test_deep_copy__annotation_label_color`: the copied label keeps `color`/`alpha`. `_copy_table` copies every column it does not remap; this test makes sure that stays true.
- [ ] **Step 2: Run** `cd lightly_studio && uv run pytest tests/api/routes/api/test_annotation_label.py tests/resolvers/dataset_resolver/test_deep_copy.py -k color`. Expected: FAIL.
- [ ] **Step 3: Add the fields.** Table comment: `# Custom display color as "#rrggbb", and its opacity in [0, 1]. Null means the default color.` In `read_annotation_labels_with_counts`, pass `color=label.color, alpha=label.alpha`.
- [ ] **Step 4: Generate the migration.** Run `make start-postgres && make migration-revision-postgresql MSG=add_annotation_label_color`.
  - `down_revision` must be the current head: today `b7d24e8f913a`, but run `uv run alembic heads` after merging main.
  - Keep only `add_column` for `color` (`AutoString()`, nullable) and `alpha` (`sa.Float()`, nullable). `downgrade` drops both.
  - Follow the style of `1791936000_8cb37a9d104e_add_image_interpolation_setting.py`.
- [ ] **Step 5: CHANGELOG** under `## [Unreleased]` → `### Changed`: `- BREAKING: DuckDB databases created before this version are not upgraded and fail to open. Re-index your data.`
- [ ] **Step 6: Verify** that the tests pass, `make migration-check-postgresql` passes, and `make static-checks` passes. **Commit** (on request).

## PR 2: Add a resolver to set an annotation class color (~115)

**Files:**
- Create: `lightly_studio/src/lightly_studio/resolvers/annotation_label_resolver/set_color.py`
- Modify: `lightly_studio/src/lightly_studio/resolvers/annotation_label_resolver/__init__.py`
- Test: `lightly_studio/tests/resolvers/annotation_label_resolver/test_set_color.py`, `test_update.py`

**Interfaces:**
- Produces: `annotation_label_resolver.set_color(session: Session, label_id: UUID, color: str | None, alpha: float | None) -> AnnotationLabelTable | None`. It returns `None` for an unknown label. It sets both fields, commits and refreshes, following `update.py`. Validation lives in the request model (PR 3).

- [ ] **Step 1: Write failing tests:**
  - `test_set_color`: the returned label and a re-read label have the values.
  - `test_set_color__clear`: `None`/`None` clears both fields.
  - `test_set_color__unknown_label` → `None`.
  - `test_update__keeps_color`: a rename with `update` keeps `color`/`alpha`.
- [ ] **Step 2–4:** Run `uv run pytest tests/resolvers/annotation_label_resolver -k color` (expect FAIL), implement, then run again with `make static-checks` (expect PASS). **Commit** (on request).

## PR 3: Add an endpoint to set an annotation class color (~110 + generated)

**Files:**
- Modify: `lightly_studio/src/lightly_studio/api/routes/api/annotation_label.py`
- Test: `lightly_studio/tests/api/routes/api/test_annotation_label.py`
- Generated: `lightly_studio_view/src/lib/api/lightly_studio_local/**`

**Interfaces:**
- Produces:
  - `class AnnotationLabelColorRequest(BaseModel)` with:
    - `color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")`
    - `alpha: float | None = Field(default=None, ge=0, le=1)`
    - a `model_validator(mode="after")` that raises `ValueError` unless both fields are set or both are `None`.
  - `set_annotation_label_color(label_id: UUID, color_input: AnnotationLabelColorRequest, session: SessionDep) -> AnnotationLabelTable` on `PUT /annotation_labels/{label_id}/color`. It raises `NotFoundError("Annotation label not found")` for an unknown label.
  - In the generated client: `setAnnotationLabelColor` and `setAnnotationLabelColorMutation`. `AnnotationLabelTable` gets `color?: string | null` and `alpha?: number | null`.

- [ ] **Step 1: Write failing tests:**
  - `test_set_annotation_label_color` (200, and a GET returns the values)
  - `test_set_annotation_label_color__clear`
  - `test_set_annotation_label_color__invalid` → 422, parametrized over:
    - `{"color": "red", "alpha": 1}`
    - `{"color": "#ff8040", "alpha": 1.5}`
    - `{"color": "#ff8040", "alpha": null}`
    - `{"color": null, "alpha": 0.5}`
  - `test_set_annotation_label_color__not_found` → 404.
  - `test_update_annotation_label__keeps_color`: set through the endpoint, rename through `PUT /annotation_labels/{id}` → the color stays.
- [ ] **Step 2–4:** Run (expect FAIL), implement, then run with `make static-checks`.
- [ ] **Step 5: Regenerate the client** with `make export-schema`, then `npm run generate-api-client` in `lightly_studio_view`. Then run `make static-checks` there. **Commit** (on request).

---

## PR 4: Seed the annotation class color picker from useColorPicker (~45)

**Purpose:** Bug fix. The legend seeds the picker with alpha 0.4, so Apply without changes dims the class.

**Files:** `lightly_studio_view/src/lib/components/AnnotationColorLegend/AnnotationColorLegend.svelte` and `AnnotationColorLegend.test.ts`. Delete `getInitialColor`, `getInitialAlpha` and the destructured `getCustomColor`/`hasCustomColor`. Pass `initialColor={picker.initialColor}` and `initialAlpha={picker.initialAlpha}`.

- [ ] **Step 1:** Write the failing test `'keeps full opacity when Apply is clicked without changes'`: open the picker, click `Apply` → `getCustomColor('cat')?.alpha === 1`.
- [ ] **Step 2–4:** Run `npx vitest run src/lib/components/AnnotationColorLegend` (expect FAIL), implement, run again. **Commit** (on request).

## PR 5: Extract the custom color store into a factory (~130, mostly moved code)

**Purpose:** Move the body of `useCustomLabelColors.ts` into a factory, with no behavior change, so PR 8 can make a second instance.

**Files:**
- Create: `lightly_studio_view/src/lib/hooks/createCustomColorStore/createCustomColorStore.ts`
- Modify: `lightly_studio_view/src/lib/hooks/useCustomLabelColors.ts`. It becomes `const store = createCustomColorStore(); export const useCustomLabelColors = () => ({ ...store, customLabelColorsStore: store.customColorsStore });`

**Interfaces:**
- Produces: `createCustomColorStore()` returns `{ customColorsStore, colorVersion, getCustomColor, setCustomColor, hasCustomColor, deleteCustomColor, clearCustomColors }`, with the current semantics.

- [ ] **Step 1:** Move the code. The existing tests in `getColorByLabel.test.ts`, `useColorPicker.test.ts` and `AnnotationColorLegend.test.ts` cover the behavior.
- [ ] **Step 2:** Run `make static-checks && make test` and expect PASS with no test changes. **Commit** (on request).

## PR 6: Keep color previews in a separate layer (~170)

**Purpose:** Today the picker writes previews into the saved map and restores a remembered value on Cancel. Anything that writes the map during a preview corrupts that value. Move previews to their own layer, owned by one picker session.

**Files:**
- Modify: `createCustomColorStore.ts`
- Create: `createCustomColorStore.test.ts`
- Modify: `lightly_studio_view/src/lib/hooks/useColorPicker/useColorPicker.svelte.ts` and `useColorPicker.test.ts`

**Interfaces:**
- Produces, added to the factory API:
  - `customColorsStore` becomes the saved layer overlaid with previews. A preview of `null` hides the saved entry, which means "show the default".
  - `setPreviewColor(name: string, color: CustomColor | null, owner: symbol): void`. It replaces any preview for `name` and records `owner`.
  - `clearPreviewColor(name: string, owner: symbol): void`. It is a no-op unless `owner` still owns the preview for `name`.
  - `clearPreviewColors(): void`: clears all previews.
  - `hasSavedColor(name: string): boolean`: reads the saved layer only.
  - `replaceSavedColors(colors: Record<string, CustomColor>): void`: replaces the saved layer and keeps previews.
  - `setCustomColor`/`deleteCustomColor` write the saved layer. `getCustomColor`/`hasCustomColor` read the overlaid view.
- `useColorPicker` changes:
  - A picker session starts at the first `setColor` after a finished session, with `owner = Symbol()`.
  - `setColor` calls `setPreviewColor(label, {color, alpha}, owner)`.
  - `finishColorChange(true)` writes the preview to the saved layer, then calls `clearPreviewColor(label, owner)`.
  - `finishColorChange(false)` only calls `clearPreviewColor`.
  - Remove `colorBeforePreview` and `isPreviewing`.

- [ ] **Step 1: Write failing tests:**
  - Factory tests:
    - `'a preview overrides the saved color'`
    - `'a null preview shows the default'`
    - `'clearPreviewColor of a stale owner keeps the newer preview'`
    - `'replaceSavedColors keeps previews'`
    - `'clearPreviewColors drops all previews'`
    - `'hasSavedColor ignores previews'`
  - Hook test: `'cancel keeps a saved color written during the preview'`. Preview `#abcdef`, then call `setCustomColor('cat', '#112233')` from outside, then cancel → `#112233`.
- [ ] **Step 2–4:** Run `npx vitest run src/lib/hooks` (expect FAIL), implement, then run `make static-checks && make test`.
- [ ] **Mocks:** `LabelsMenu.test.ts:40` and `SampleDetailsClassificationSegment.test.ts:120` mock `useCustomLabelColors` partially. `useColorPicker` reads only `customLabelColorsStore` during render; the new functions run only when a test opens a picker. Expected: no mock change. If `make test` fails there, add `setPreviewColor`/`clearPreviewColor: vi.fn()` to those mocks. **Commit** (on request).

## PR 7: Color annotations by source through getColorBySource (~145)

**Purpose:** Readers that color by source say so. In this PR the source store is still the class store, so behavior does not change. PR 8 splits the stores.

I checked every caller of `getColorByLabel` and `customLabelColorsStore`. Only these color by source: `SampleAnnotation`, `SampleAnnotations` + `AnnotationCanvas`, and `SampleClassificationPills`. The other callers use class names or non-source names and stay on `getColorByLabel`: `SampleDetailsImageContainer`, `AnnotationItem`, point cloud `useWorkspaceSceneData`, `videoEvents`, `useVideoFrameAnnotations` and `plotColorUtils`.

**Files:**
- Create: `lightly_studio_view/src/lib/hooks/useCustomSourceColors.ts`. For now it returns `useCustomLabelColors()` with `customSourceColorsStore` as the alias. Comment: `// Shares the class color store until source colors get their own store.`
- Create: `lightly_studio_view/src/lib/utils/getColorBySource.ts`. Modify `getColorByLabel.ts`: extract `getDefaultColor(name, alpha)` (palette + hash) and export it. Export both from `lightly_studio_view/src/lib/utils/index.ts` and `lightly_studio_view/src/lib/hooks/index.ts`.
- Modify `lightly_studio_view/src/lib/components/SampleAnnotation/SampleAnnotation.svelte`:
  - Replace `colorLabel` with `colorSource: string | undefined`.
  - When it is set, the stroke, fill, text color and mask alpha use `$customSourceColorsStore[colorSource]` + `getColorBySource`. Otherwise they use the class store + `getColorByLabel`.
- Modify `lightly_studio_view/src/lib/components/SampleAnnotations/index.svelte` and `lightly_studio_view/src/lib/components/AnnotationCanvas/AnnotationCanvas.svelte`:
  - Add `colorBySource?: boolean` to the canvas annotation type, where `InstanceAnnotation`/`ObjectDetectionAnnotation` are declared.
  - `SampleAnnotations` sets it when it swaps in the source name.
  - In the canvas, `resolveLabelColor` picks the map and the color function by the flag. The canvas also re-renders on `$customSourceColorsStore` (lines ~225, ~359).
- Modify `lightly_studio_view/src/lib/components/SampleClassificationPills/getSampleClassificationPills.ts`: add `colorBySource: boolean` to `SampleClassificationPill`.
- Modify `SampleClassificationPills.svelte`: `getPillColor` picks the store and color function by `pill.colorBySource`, keyed by `pill.colorKey`. Today it reads the class map by `pill.label` even in source mode.

**Interfaces:**
- Produces:
  - `getColorBySource(sourceName: string, alpha = 1): ColorPair`
  - `getDefaultColor(name: string, alpha: number): ColorPair`
  - `useCustomSourceColors()`: the same API as `useCustomLabelColors()`, plus `customSourceColorsStore`.

- [ ] **Step 1: Write or update failing tests:**
  - `getColorBySource.test.ts`: `'uses a custom source color'` and `'falls back to getDefaultColor'`.
  - `SampleAnnotations/index.test.ts` (~309–340): spy on `getColorBySource` for source names. In the enforce-class case, `getColorBySource` is not called.
  - `SampleAnnotation.test.ts` (~186): the source color comes from `getColorBySource('Predictions', 1)`.
  - `getSampleClassificationPills.test.ts`: the expected pills include `colorBySource`. A new pill test checks that a source pill uses the color for `colorKey`.
- [ ] **Step 2–4:** Run the suites (expect FAIL), implement, then run `make static-checks && make test`. **Commit** (on request).

## PR 8: Keep annotation source colors in their own store (~110)

**Purpose:** Split the stores, so a source and a class with the same name no longer overwrite each other.

**Files:**
- Modify: `lightly_studio_view/src/lib/hooks/useCustomSourceColors.ts`. It becomes its own `createCustomColorStore()` instance; remove the comment from PR 7.
- Modify: `useColorPicker.svelte.ts`, `useColorPickerTestWrapper.test.svelte`, `useColorPicker.test.ts`, `AnnotationColorLegend.svelte` (`kind: 'class'`), and `lightly_studio_view/src/lib/components/SideMenu/ColorMarker/ColorMarker.svelte` + `ColorMarker.test.ts` (`kind: 'source'`)

**Interfaces:**
- Produces: `export type ColorKind = 'class' | 'source'` and `useColorPicker(getLabel: () => string, options: { kind: ColorKind })`.
  - `'class'` uses `useCustomLabelColors` + `getColorByLabel`.
  - `'source'` uses `useCustomSourceColors` + `getColorBySource`.

- [ ] **Step 1: Write failing tests:**
  - `ColorMarker.test.ts`, `'a source color does not change the class color with the same name'`: class `Predictions` = `#111111`, Apply `#0000ff` in `ColorMarker` → the class store keeps `#111111` and the source store has `#0000ff`. Switch the existing `ColorMarker` assertions to `useCustomSourceColors()`.
  - `SampleAnnotation.test.ts`, `'a class color does not recolor the source in source mode'`.
- [ ] **Step 2–4:** Run (expect FAIL), implement, then run `make static-checks && make test`.
- [ ] **Mocks:** a `kind: 'class'` picker still reads only `customLabelColorsStore` during render, so the partial mocks need no change. Nothing mocks `useCustomSourceColors`. **Commit** (on request).

## PR 9: Add "Reset to default" to the color picker (~115)

**Files:**
- Modify: `lightly_studio_view/src/lib/components/ui/color-picker/color-picker.svelte` and `color-picker.test.ts`
- Modify: `useColorPicker.svelte.ts`, `useColorPickerTestWrapper.test.svelte`, `useColorPicker.test.ts`
- Modify: `AnnotationColorLegend.svelte` and `ColorMarker.svelte`. Both pass `onReset={picker.hasCustomColor ? picker.resetColor : undefined}`.
- Modify mocks: `LabelsMenu.test.ts:40` and `SampleDetailsClassificationSegment.test.ts:120` add `hasSavedColor: () => false`. `hasCustomColor` reads it during render, so the partial mocks would fail without it.
- Modify: `CHANGELOG.md` `### Added`: `- Reset a custom color to the default color in the color picker.`

**Interfaces:**
- `ColorPicker` gets the prop `onReset?: () => void`. When it is set, a `Button` (`variant="ghost"`, same size classes as Cancel, left in the actions row) shows `Reset to default`. Click: `cancelScheduledPreview()`, `onReset()`, `hasPreviewed = false`, `isOpen = false`. It does not call `onClose` or `onChange`.
- `useColorPicker` adds:
  - `hasCustomColor: boolean`, from `hasSavedColor` of its store, reactive.
  - `resetColor(): void`: ends any open session (clears its preview) and deletes the saved entry.

- [ ] **Step 1: Write failing tests:**
  - `'shows Reset to default only when onReset is set'`
  - `'Reset to default calls onReset and closes without onClose'`
  - `'resetColor removes the custom color'`: the border equals `getColorByLabel('cat', 1).color`.
- [ ] **Step 2–4:** Run, implement, then run `make static-checks && make test`. **Commit** (on request) with a screenshot.

## PR 10: Let the color picker save changes asynchronously (~140)

**Purpose:** Prefactor for PR 11, which is the first caller. This PR adds an optional async commit to `useColorPicker`. The hard cases are a save still pending while the picker reopens, and two saves overlapping. `color-picker.svelte:286` closes the panel at once, so the user can preview again while a save is pending.

**Files:**
- Modify: `createCustomColorStore.ts` + test
- Modify: `useColorPicker.svelte.ts`, `useColorPickerTestWrapper.test.svelte`, `useColorPicker.test.ts`

**Interfaces:**
- The factory adds:
  - `beginSave(name: string): number`: returns the next save sequence number for `name`.
  - `setSavedColor(name: string, color: CustomColor | undefined, seq: number): void`: applies only if `seq` is greater than the last applied sequence for `name`. `undefined` deletes the entry.
  - `replaceSavedColors` (from PR 6) keeps the sequence counters.
- `useColorPicker(getLabel, options: { kind: ColorKind; onCommit?: (color: CustomColor | undefined) => Promise<void> })`:
  - `finishColorChange(applied: boolean): Promise<void>`. On Apply, it captures `owner`, the preview value and `seq = beginSave(label)`, then ends the session (the next `setColor` gets a new owner). It awaits `onCommit?.(value)`. On success it calls `setSavedColor(label, value, seq)`. In all cases it then calls `clearPreviewColor(label, owner)`. A rejection is not rethrown; the owner of `onCommit` shows the toast (PR 11).
  - `resetColor(): Promise<void>` does the same with a new owner, `setPreviewColor(label, null, owner)` and `value = undefined`.

- [ ] **Step 1: Write failing tests:**
  - `'apply calls onCommit with the applied color'`
  - `'shows the preview until onCommit settles'`
  - `'reverts to the saved color when onCommit rejects'`
  - `'keeps the saved color when a reset fails'`
  - `'reopening while a save is pending keeps the new preview'`: Apply `#aaaaaa` with a deferred `onCommit`, then `setColor('#bbbbbb')`, then resolve the first commit → the effective color is `#bbbbbb` and the saved color is `#aaaaaa`.
  - `'an older save that resolves late does not overwrite a newer one'`: Apply A, then Apply B, both deferred. Resolve B, then A → the saved color is B.
  - Factory test: `'setSavedColor ignores an older sequence'`.
- [ ] **Step 2–4:** Run, implement, then run `make static-checks && make test`. **Commit** (on request).

## PR 11: Save annotation class colors in the dataset (~195)

**Purpose:** Apply and Reset in the class legend save to the server. Colors stay in the local saved layer, as before, and now survive on the server. They do not load on reload yet (PR 12). Session colors are not lost, because nothing replaces the saved layer yet.

**Files:**
- Modify: `lightly_studio_view/src/lib/hooks/useCustomLabelColors.ts`. Add the name→ID map. Create `useCustomLabelColors.test.ts`.
- Modify: `lightly_studio_view/src/routes/datasets/[dataset_id]/[collection_type]/[collection_id]/+layout.svelte`, next to `annotationLabelsQuery` (~line 338): `$effect(() => { if (annotationLabelsData) setAnnotationClasses(datasetId, annotationLabelsData); });`
- Create: `lightly_studio_view/src/lib/hooks/useSaveAnnotationClassColor/useSaveAnnotationClassColor.svelte.ts` and `useSaveAnnotationClassColor.svelte.test.ts`. Export from `lightly_studio_view/src/lib/hooks/index.ts`.
- Modify: `AnnotationColorLegend.svelte`: `useColorPicker(() => labelName, { kind: 'class', onCommit: (color) => saveClassColor(labelName, color) })`
- Modify: `CHANGELOG.md`. Extend the existing "Annotation classes" tab entry, or add `- Annotation class colors are saved in the dataset.`

Test stubs (no `QueryClientProvider` exists in tests). Add `vi.mock('$lib/hooks/useSaveAnnotationClassColor/useSaveAnnotationClassColor.svelte', () => ({ useSaveAnnotationClassColor: () => ({ saveClassColor: vi.fn().mockResolvedValue(undefined) }) }))` to every test that renders the legend:
- `lightly_studio_view/src/lib/components/AnnotationColorLegend/AnnotationColorLegend.test.ts`
- `lightly_studio_view/src/lib/components/LabelsMenu/LabelsMenu.test.ts`
- `lightly_studio_view/src/lib/components/Settings/AnnotationClassesTab/AnnotationClassRow/AnnotationClassRow.test.ts`
- `lightly_studio_view/src/lib/components/Settings/AnnotationClassesTab/AnnotationClassesTab.test.ts` (renders rows)
- `lightly_studio_view/src/lib/components/Settings/SettingsDialog.test.ts` (opens the Annotation classes tab)
- `lightly_studio_view/src/lib/components/SampleDetails/SampleDetailsClassificationSegment/SampleDetailsClassificationSegment.test.ts`
- `lightly_studio_view/src/lib/components/SampleDetails/SampleDetailsSidePanel/SampleDetailsSidePanelAnnotation/SampleDetailsSidePanelAnnotation.test.ts`
- `lightly_studio_view/src/lib/components/SampleDetails/SampleDetailsAnnotationSegment/SampleDetailsAnnotationSegment.test.ts` (renders `SampleDetailsSidePanelAnnotation`)

These do not need the stub: `VideoDetails.test.ts` stubs `SampleDetailsClassificationSegment`, `SampleDetailsPanel.test.ts` stubs `SampleDetailsSidePanel`, `layout.workspace.test.ts` stubs `LabelsMenu`, and `MenuDialogHost.test.ts` stubs `SettingsDialog`. After the change, run `make test` and add the stub to any other suite that fails with "No QueryClient set".

**Interfaces:**
- Consumes: `setAnnotationLabelColorMutation` (PR 3) and `onCommit` (PR 10).
- Produces:
  - `setAnnotationClasses(datasetId: string, classes: Pick<AnnotationLabelTable, 'annotation_label_id' | 'annotation_label_name' | 'color' | 'alpha'>[]): void`. In this PR it only replaces the name→ID map. PR 12 extends it.
  - `getAnnotationClassId(name: string): string | undefined`
  - `useSaveAnnotationClassColor(): { saveClassColor: (name: string, color: CustomColor | undefined) => Promise<void> }`:
    - Unknown name: `toast.error('Could not save the annotation class color.')`, then throw.
    - Otherwise: `mutateAsync({ path: { label_id }, body: { color: color?.color ?? null, alpha: color?.alpha ?? null } })`.
    - `onError`: the same toast.
    - `onSettled`: invalidate only the class-list queries, with a predicate that is true when `(q.queryKey[0] as { _id?: string })?._id` is `'readAnnotationLabels'` or `'readAnnotationLabelsWithCounts'`.

- [ ] **Step 1: Write failing tests.** For the hook, mock `@tanstack/svelte-query` as in `useAnnotationClasses.svelte.test.ts`.
  - `'saves the color for the class ID'`
  - `'clears the color on reset'`
  - `'rejects and toasts for an unknown class'`
  - `'invalidates only the class list queries'`
  - In `useCustomLabelColors.test.ts`: `'setAnnotationClasses maps names to IDs'`
- [ ] **Step 2–4:** Run (expect FAIL), implement, add the stubs, then run `make static-checks && make test`. **Commit** (on request).

## PR 12: Load annotation class colors from the dataset (~125)

**Purpose:** Colors survive a reload and show for all users. Renames keep the color because the server keys it by class ID, so the rename workaround goes away.

**Files:**
- Modify: `useCustomLabelColors.ts` + test
- Modify: `lightly_studio_view/src/lib/components/Settings/AnnotationClassesTab/useAnnotationClasses/useAnnotationClasses.svelte.ts` and its test.
  - Remove the color move in `renameClass`, the `useCustomLabelColors` mock, and the two color tests (`'renameClass moves the custom color to the new name'` and `'renameClass keeps colors when the rename fails'`).
  - Change `renameClass` to `(labelId: string, name: string)`.
- Modify: `lightly_studio_view/src/lib/components/Settings/AnnotationClassesTab/AnnotationClassList/AnnotationClassList.svelte` (~line 62). The `onRename` prop type and adapter drop `oldName`. `AnnotationClassRow` already passes only the new name and does not change.
- Modify: `CHANGELOG.md`: the class color entry from PR 11 now says the colors are shared by all users of the dataset.

**Interfaces:**
- `setAnnotationClasses(datasetId, classes)` also calls `replaceSavedColors({ [name]: { color, alpha: alpha ?? 1 } })` for every class with a non-null `color`. When `datasetId` differs from the previous call, it first calls `clearPreviewColors()`. A same-dataset call keeps previews.

- [ ] **Step 1: Write failing tests:**
  - `'loads saved colors'`: `cat` has a color; `dog` with a null color has none.
  - `'replaces the previous classes'`: load `cat`, then load `kitty` with the same ID → `cat` has no color, `kitty` has the color. This is the rename case.
  - `'a refetch of the same dataset keeps an open preview'`: preview `cat` = `#abcdef`, reload `ds-1` with saved `#112233` → the effective color is `#abcdef`.
  - `'switching datasets drops previews and colors'`: preview `cat` in `ds-1`, then call `setAnnotationClasses('ds-2', [])` → `getCustomColor('cat')` is undefined.
- [ ] **Step 2–4:** Run (expect FAIL), implement, then run `make static-checks && make test`.
- [ ] **Step 5: Manual check.** Run `cd lightly_studio && make build-lightly_studio_view` once and use a fresh DuckDB file. Then check:
  - Set a class color, reload → the color is kept.
  - Rename the class → the color is kept.
  - Reset → the default color shows after a reload.
  - Add a class while a legend picker is open → the preview stays.
  - Switch dataset with a picker open → no color carries over.
  - Set a source color → the class color does not change.
- **Commit** (on request).

---

## Decisions

- Plot categories keep using `getColorByLabel`; a class with the same name recolors them, as today.
- PR 11 stubs the save hook per test file, not globally in `src/setupTests.ts`, so tests that need the real hook still see it.
