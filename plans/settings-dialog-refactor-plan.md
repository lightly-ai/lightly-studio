# Plan: Settings Dialog Refactor

## Context

`SettingsDialog.svelte` has grown into a 470-line component that owns dialog wiring, editable state, settings-store mapping, shortcut recording, save payload construction, and all row markup. The frontend guidelines prefer components under 100 lines, `.svelte.ts` files for component logic, small testable parts, and reusable project-specific components when combining UI primitives.

The goal is to reduce complexity without changing settings behavior. Keep the refactor stacked so each PR is reviewable on its own.

## Current Problems

- Shortcut rows are manually duplicated, which already produced duplicate `id="toggle-edit-mode"` values.
- Store-to-form mapping and form-to-save-payload mapping are embedded in the component and must be edited in multiple places for every new setting.
- Shortcut recording uses `string | null` and casts instead of a typed shortcut key union.
- The `initialized` guard hydrates local state only once, which can leave the dialog stale if settings are reloaded while the component stays mounted.
- Tests mostly exercise the full dialog DOM, so small mapping mistakes are harder to isolate.

## Target Shape

```
src/lib/components/Settings/
  SettingsDialog.svelte
  SettingsDialog.test.ts
  settingsDialogConfig.ts
  settingsDialogState.svelte.ts
  settingsDialogState.test.ts
  ShortcutSettingRow/
    ShortcutSettingRow.svelte
    ShortcutSettingRow.test.ts
  SettingsFieldRow/
    SettingsFieldRow.svelte
```

The exact file split can be adjusted during implementation, but each PR should move toward:

- `SettingsDialog.svelte` as the dialog shell and section composition.
- `settingsDialogState.svelte.ts` as the local editable state and save payload adapter.
- `settingsDialogConfig.ts` as the single source of row definitions.
- Small presentational row components for repeated markup.

## Stacked PR Plan

Instruction: Update this file with after implementing every step. Mark the step as
done and add important learnings for next step implementation.

### PR 1: Extract Settings Dialog Mapping Helpers - Done

Scope:

- Create `settingsDialogState.svelte.ts` or a plain helper file if no runes are needed yet.
- Define explicit local form types:
  - `ShortcutSettingKey`
  - `SettingsDialogFormState`
  - `RenderingMode`
  - `ThumbnailQualityMode`
- Add helpers:
  - `createSettingsDialogFormState(settings)`
  - `createSettingsSavePayload(formState)`
  - `normalizeShortcutKey(event)`

Implementation notes:

- Preserve all current defaults:
  - hide annotations: `v`
  - go back: `Escape`
  - toggle edit mode: `e`
  - toolbar selection: `s`
  - toolbar brush: `r`
  - toolbar eraser: `x`
  - rendering: `contain`
  - thumbnail quality: `raw`
  - text labels: `false`
  - sample filenames: current behavior is `false` in the dialog fallback, even though the hook default is `true`; call this out in the PR if kept unchanged.
  - segmentation boxes: `true`
- Do not change the UI yet, except replacing inline mapping code with helper calls.
- Keep the save payload identical to the current one.

Tests:

- Add `settingsDialogState.test.ts` for:
  - default mapping when settings fields are missing
  - exact save payload shape
  - shortcut normalization for space, lowercase letters, uppercase with caps lock, and non-letter keys
- Keep existing `SettingsDialog.test.ts` passing.

Expected size:

- Around 120 to 180 lines including tests.

Learnings:

- `settingsDialogState.ts` now owns form defaults, save payload construction, and shortcut key normalization.
- The dialog fallback for `show_sample_filenames` remains `false`, even though `useSettings.ts` still defaults that setting to `true`.
- Toolbar selection, drag, bounding box, and segmentation mask now have explicit helper defaults (`s`, `d`, `b`, `m`) for missing fields, matching the hook defaults and avoiding undefined form values in helper tests.
- The remaining duplicated shortcut row IDs are intentionally untouched for PR 2.

### PR 2: Add Shortcut Settings Config and Reusable Row

Scope:

- Create `settingsDialogConfig.ts` with a typed `shortcutSettings` array.
- Create `ShortcutSettingRow.svelte`.
- Replace the repeated shortcut markup in `SettingsDialog.svelte` with an `{#each}` over config.

Implementation notes:

- Give every shortcut a unique stable `id`.
- Keep labels and displayed shortcut values unchanged.
- Keep the disabled `Change brush size` row in the config or render it as a separate static row.
- The row component should receive explicit props:
  - `id`
  - `label`
  - `value`
  - `isRecording`
  - `disabled`
  - `onStartRecording`
- Do not change shortcut-recording behavior in this PR.

Tests:

- Add `ShortcutSettingRow.test.ts` for normal, recording, disabled, and click behavior.
- Update dialog tests to query by unique labels or IDs instead of relying on duplicated IDs.
- Add a small assertion that all shortcut controls have unique IDs if practical.

Expected size:

- Around 100 to 160 lines changed.

### PR 3: Extract Display and Annotation Field Rows

Scope:

- Extract the repeated two-column row layout into `SettingsFieldRow.svelte`.
- Use it for:
  - grid view rendering select
  - sample filename switch
  - thumbnail quality select
  - segmentation boxes switch
  - annotation text labels switch

Implementation notes:

- Keep `Select`, `Switch`, and `Label` behavior unchanged.
- Do not over-generalize select/switch logic yet; this PR should primarily remove repeated layout markup.
- Keep labels associated with controls through `for` and `id`.
- Keep `SettingsDialog.svelte` readable even if this PR does not get it under 100 lines yet.

Tests:

- Existing dialog tests should continue to cover the visible fields and save payload.
- Add row-level tests only if the component contains behavior beyond label/control layout.

Expected size:

- Around 80 to 140 lines changed.

### PR 4: Move Dialog State Machine Out of the Component

Scope:

- Move local editable state, hydration, recording state, and submit payload construction into `settingsDialogState.svelte.ts`.
- Keep `SettingsDialog.svelte` responsible for:
  - opening and closing the dialog
  - passing state/actions to row components
  - rendering dialog header/footer
  - calling `saveSettings`

Implementation notes:

- Replace `initialized` with an explicit synchronization rule:
  - hydrate when settings finish loading and the form is not dirty, or
  - hydrate each time the dialog opens from the latest store values.
- Prefer the second rule if it is simpler and does not discard in-progress edits while the dialog is open.
- Track dirty state only if needed to prevent overwriting user edits while the dialog is open.
- Keep `recordingShortcut` typed as `ShortcutSettingKey | null`.

Tests:

- Expand `settingsDialogState.test.ts` to cover:
  - opening with latest settings hydrates form state
  - closing clears recording state
  - recording a shortcut updates only the targeted key
  - save payload includes all current form values
- Keep one or two high-level dialog tests for integration behavior instead of duplicating every helper test.

Expected size:

- Around 150 to 220 lines changed.

### PR 5: Tighten Dialog Tests and Accessibility Queries

Scope:

- Update `SettingsDialog.test.ts` to use user-visible labels and roles consistently.
- Remove tests that only duplicate helper coverage.
- Add coverage for the previously duplicated ID risk.

Implementation notes:

- Prefer `getByLabelText`, `getByRole`, and section text over `document.getElementById`.
- Keep at least these integration tests:
  - closed by default
  - opens through `useSettingsDialog`
  - records and saves one shortcut
  - toggles and saves one switch
  - save button shows saving state
  - cancel closes without saving
- If select interactions are hard through the component library, test select payload mapping in helper tests and keep only a smoke assertion in the dialog test.

Expected size:

- Net negative or small positive line count.

### PR 6: Final Cleanup and Barrel Exports

Scope:

- Export any new Settings subcomponents from `Settings/index.ts` only if they are intended as public module API.
- Remove dead comments and any temporary compatibility code.
- Run full frontend validation.

Implementation notes:

- Keep internal helper files unexported from barrels unless another module needs them.
- Check final component lengths. If `SettingsDialog.svelte` is still well above 100 lines, split section components:
  - `KeyboardShortcutsSection.svelte`
  - `DisplaySettingsSection.svelte`
  - `AnnotationSettingsSection.svelte`
- Do not combine this with behavior changes.

Expected size:

- Around 20 to 80 lines changed, mostly cleanup.

## Validation

Run from `lightly_studio_view`:

```bash
make static-checks
make test
```

Targeted checks while iterating:

```bash
npm run test:unit -- --run src/lib/components/Settings/settingsDialogState.test.ts
npm run test:unit -- --run src/lib/components/Settings/ShortcutSettingRow/ShortcutSettingRow.test.ts
npm run test:unit -- --run src/lib/components/Settings/SettingsDialog.test.ts
```

Manual verification:

1. Open settings and confirm all current labels and values still render.
2. Record a shortcut and confirm it updates only after pressing a key.
3. Cancel after editing and confirm no save request is made.
4. Save after editing shortcuts, display settings, and annotation settings; confirm the dialog closes.
5. Reopen settings and confirm values hydrate from the latest store values.
6. Check that every label targets a unique control ID.

## PR Checklist

- One purpose per PR.
- Keep each PR behavior-preserving unless its title explicitly says otherwise.
- Include tests with every extracted helper or component that owns behavior.
- Keep generated files out of the PR unless the backend schema changes.
- Avoid broad formatting churn in `SettingsDialog.svelte`; moved code should remain easy to review.
