# Camera Switch Shortcuts (ENT-638) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Step through the selected cameras of the point cloud workspace with configurable keys and buttons, even during playback, with the open camera kept in the URL hash.

**Architecture:** The route owns `{ tick, camera }` and always writes the whole hash from both values. The workspace passes the open camera down to `CameraProjectionStrip`. The strip now renders the one enlarged-camera dialog itself; the per-tile dialogs go away. Previous/next keys are two new recordable settings, stored in the backend `setting` table.

**Tech Stack:** SvelteKit 2 / Svelte 5 runes, TanStack Query, vitest + @testing-library/svelte; FastAPI + SQLModel + Alembic, pytest.

**Spec:** `.experimental/superpowers/specs/2026-11-26-camera-switch-shortcuts-design.md`

## Global Constraints

- One PR for backend + frontend.
- URL: `#tick=<n>&camera=<group_component_name>`. Camera name, never `channel_id`.
- Default keys: previous camera `[`, next camera `]`. Fixed alternates: Shift+← / Shift+→. Fixed: `1`–`9` open camera N in strip order.
- Navigation order = selected cameras in strip order. Prev/next wrap around.
- No new key may use `C` (Create cuboid), Space, plain arrows, W/A/S/D, `e`.
- Shortcuts are ignored when the target is a text input (`isTextInputTarget`) or Alt/Ctrl/Meta is held.
- Switching camera never pauses or restarts playback.
- Opening the dialog adds one history entry. Switching camera replaces it. Closing removes it (browser Back closes the dialog).
- User-facing copy: dialog header `Camera: <name> · <i> / <n>`; settings rows "Previous camera", "Next camera", "Previous / next camera (alt)" = `Shift + ← / →`, "Open camera 1–9" = `1–9`; button aria-labels "Previous camera" / "Next camera".
- Follow `python-guide`, `backend-guide`, `frontend-guide`, `clean-code`, `changelog` skills for the paths touched.

## Review Focus

1. A playback tick write right after a camera switch (before `page.url` updates) must keep `camera` in the hash → Task 5 test `keeps camera when tick changes right after a switch`.
2. The open camera gets deselected in the Camera filter while the dialog is open → the dialog closes and `camera` is removed from the hash → Task 4 test `closes when the open camera is deselected`.
3. Reload with `#camera=X` before the channel summary has loaded → must not be cleared as "invalid" while channels are still empty → Task 4 test `keeps the open camera while channels are loading`.
4. `[` / `]` typed into a text input inside or behind the dialog → no switch → Task 3 test `ignores keys from text inputs`.
5. Browser Back after switching cameras 3 times → closes the dialog in one step, does not walk through cameras → Task 5 test `closing after switches pops a single history entry`.

---

### Task 1: Backend settings for camera keys

**Files:**
- Modify: `lightly_studio/src/lightly_studio/models/settings.py` (`SettingBase` toolbar-shortcut block, `SettingDefaults`)
- Modify: `lightly_studio/src/lightly_studio/resolvers/settings_resolver.py` (`set_settings`)
- Create: `lightly_studio/src/lightly_studio/migrations/versions/<ts>_<rev>_add_camera_shortcut_settings.py`
- Modify: `lightly_studio/openapi.json` (regenerated), `lightly_studio_view/src/lib/api/lightly_studio_local/*.gen.ts` (regenerated)
- Test: `lightly_studio/tests/resolvers/test_settings_resolver.py`

**Interfaces:**
- Produces: `SettingView.key_previous_camera: str` (default `"["`), `SettingView.key_next_camera: str` (default `"]"`); same names in the generated TS `SettingView`.

- [ ] **Step 1: Write failing tests** in `test_settings_resolver.py`:
  - extend `test_get_settings_creates_default_settings` with `assert settings.key_previous_camera == "["` and `assert settings.key_next_camera == "]"`.
  - new `test_set_settings_updates_camera_shortcuts`: get settings, `model_copy(update={"key_previous_camera": "q", "key_next_camera": "r"})`, `set_settings`, re-`get_settings`, assert both values persisted.
- [ ] **Step 2: Run** `cd lightly_studio && uv run pytest tests/resolvers/test_settings_resolver.py -v`. Expected: FAIL (attribute missing).
- [ ] **Step 3: Implement.** In `SettingBase` add `key_previous_camera: str = Field(description="Key to show the previous camera in the enlarged camera view")` and `key_next_camera` (same, "next"). In `SettingDefaults` add `Field(default="[")` / `Field(default="]")`. In `set_settings` copy both next to the toolbar keys. Migration modelled on `1791936000_8cb37a9d104e_add_image_interpolation_setting.py`: `down_revision = "37ee066f0639"` (current head — verify with `uv run alembic heads`), `op.add_column("setting", sa.Column("key_previous_camera", sa.String(), nullable=False, server_default="["))`, same for next with `"]"`; downgrade drops both. Revision id: 12 random hex chars; filename prefix = current unix timestamp.
- [ ] **Step 4: Run** the tests again → PASS. Run `cd lightly_studio && make export-schema`, then `cd lightly_studio_view && npm run generate-api-client`. Expected: `types.gen.ts` `SettingView` contains `key_previous_camera: string`.
- [ ] **Step 5: Run** `cd lightly_studio && make static-checks` → clean. If a migration check target exists for DuckDB/Postgres in CI, run `make migration-check-postgresql` when Docker is available; otherwise note it.
- [ ] **Step 6: Commit** `feat: add previous/next camera shortcut settings`.

### Task 2: Settings UI rows for camera keys

**Files:**
- Modify: `lightly_studio_view/src/lib/hooks/useSettings.ts` (`DEFAULT_SETTINGS`)
- Modify: `lightly_studio_view/src/lib/components/Settings/settingsDialogConfig.ts`
- Modify: `lightly_studio_view/src/lib/components/Settings/settingsDialogState.svelte.ts` (state type, load mapping ~l.50, save mapping ~l.81, defaults ~l.117)
- Modify: `lightly_studio_view/src/lib/components/Settings/ShortcutsTab/ShortcutsTab.svelte`
- Test: existing ShortcutsTab / settingsDialogState tests next to those files (add cases there)

**Interfaces:**
- Consumes: `SettingView.key_previous_camera`, `SettingView.key_next_camera` (Task 1).
- Produces: `ShortcutSettingKey` gains `'keyPreviousCamera' | 'keyNextCamera'`; exports `pointCloudShortcuts: readonly ShortcutSettingConfig[]` and `staticPointCloudShortcuts: readonly StaticShortcutConfig[]`.

- [ ] **Step 1: Write failing tests:**
  - ShortcutsTab renders a "Point cloud" group with rows "Previous camera" (value `[`), "Next camera" (`]`), "Previous / next camera (alt)" (`Shift + ← / →`, disabled), "Open camera 1–9" (`1–9`, disabled).
  - settingsDialogState: recording `keyNextCamera` then saving sends `key_next_camera` with the recorded key.
- [ ] **Step 2: Run** `cd lightly_studio_view && npx vitest run src/lib/components/Settings` → FAIL.
- [ ] **Step 3: Implement.** Config: `pointCloudShortcuts = [{ id: 'previous-camera', label: 'Previous camera', key: 'keyPreviousCamera' }, { id: 'next-camera', label: 'Next camera', key: 'keyNextCamera' }]`; `staticPointCloudShortcuts = [{ id: 'camera-alt', label: 'Previous / next camera (alt)', displayValue: 'Shift + ← / →' }, { id: 'open-camera-n', label: 'Open camera 1–9', displayValue: '1–9' }]`. Add `<SettingsGroup title="Point cloud" columns={2}>` after "Annotation tools". Wire both keys through state/load/save/defaults and `useSettings` `DEFAULT_SETTINGS` (`'['`, `']'`).
- [ ] **Step 4: Run** the tests → PASS.
- [ ] **Step 5: Commit** `feat: show camera shortcuts in settings`.

### Task 3: Camera navigation helpers and dialog controls

**Files:**
- Create: `lightly_studio_view/src/lib/components/PointCloudLabelingWorkspace/CameraProjectionStrip/cameraNavigation/cameraNavigation.ts`
- Test: `.../cameraNavigation/cameraNavigation.test.ts`
- Modify: `.../CameraProjectionStrip/CameraProjectionFrame/CameraProjectionDialog.svelte`
- Test: `.../CameraProjectionFrame/CameraProjectionDialog.test.ts` (create)

**Interfaces:**
- Produces:
  - `getAdjacentCamera(names: readonly string[], current: string, direction: 'previous' | 'next'): string | undefined` — wraps; returns `undefined` when `names.length < 2` or `current` not in `names`.
  - `getCameraKeyAction(event: KeyboardEvent, keys: { previous: string; next: string }): 'previous' | 'next' | undefined` — `undefined` for text-input targets (`isTextInputTarget`) or Alt/Ctrl/Meta; matches `event.key` against `keys` (case-insensitive) and Shift+ArrowLeft/ArrowRight.
  - `getCameraForDigit(event: KeyboardEvent, names: readonly string[]): string | undefined` — `1`–`9` → `names[n-1]`; `undefined` for other keys, modifiers (incl. Shift), text inputs, `n > names.length`.
  - `CameraProjectionDialog` new props: `position: { index: number; total: number }` (1-based index), `onPrevious?: () => void`, `onNext?: () => void`, `previousKey: string`, `nextKey: string`.

- [ ] **Step 1: Write failing unit tests** (`cameraNavigation.test.ts`):
  - `getAdjacentCamera(['A','B','C'], 'C', 'next') === 'A'`; `('A','previous') === 'C'`; `('B','next') === 'C'`.
  - single camera: `getAdjacentCamera(['A'], 'A', 'next') === undefined`.
  - current missing: `getAdjacentCamera(['A','B'], 'X', 'next') === undefined`.
  - `getCameraKeyAction` for `[`, `]`, remapped `q`, Shift+ArrowRight → `'next'`, plain ArrowRight → `undefined`, Ctrl+`]` → `undefined`, target `<input>` → `undefined` (test name `ignores keys from text inputs`).
  - `getCameraForDigit`: `'2'` with `['A','B']` → `'B'`; `'3'` → `undefined`; `'0'` → `undefined`; target `<input>` → `undefined`.
- [ ] **Step 2: Run** `npx vitest run src/lib/components/PointCloudLabelingWorkspace/CameraProjectionStrip/cameraNavigation` → FAIL.
- [ ] **Step 3: Implement** the three helpers.
- [ ] **Step 4: Write failing dialog tests:** header shows `Camera: CAM_FRONT · 2 / 5`; clicking "Next camera" calls `onNext`; pressing `]` inside the dialog calls `onNext`; with `onPrevious`/`onNext` undefined the buttons are disabled; Space still calls `onPlaybackToggle` and `]` does not.
- [ ] **Step 5: Implement dialog changes.** Header title `Camera: {label} · {position.index} / {position.total}`. Two icon buttons (`ChevronLeft` / `ChevronRight`, aria-labels "Previous camera" / "Next camera", `title="Shortcut: {key}"`) left of `ProjectionControls`. In `handleKeydown`, before the Space branch: `const action = getCameraKeyAction(event, { previous: previousKey, next: nextKey })`; on a match `preventDefault`, `stopPropagation`, call the callback.
- [ ] **Step 6: Run** both test files → PASS.
- [ ] **Step 7: Commit** `feat: add previous/next camera controls to the camera dialog`.

### Task 4: One dialog in the strip, open camera through the workspace

**Files:**
- Modify: `.../CameraProjectionStrip/CameraProjectionFrame/CameraProjectionFrame.svelte` (drop `isEnlarged` + dialog; add `onEnlarge?: () => void`)
- Modify: `.../CameraProjectionStrip/CameraProjectionStrip.svelte`
- Modify: `.../PointCloudWorkspaceMainColumn.svelte` (pass new props)
- Modify: `.../workspaceOptions.d.ts`, `.../pointCloudWorkspaceLayoutContext.svelte.ts`, `.../createWorkspaceController.svelte.ts`, `.../PointCloudLabelingWorkspace.svelte`
- Test: `.../CameraProjectionStrip/CameraProjectionStrip.test.ts`, `.../CameraProjectionFrame/CameraProjectionFrame.test.ts` (update)

**Interfaces:**
- Consumes: Task 3 helpers and dialog props; `useSettings().settingsStore` for `key_previous_camera` / `key_next_camera`.
- Produces:
  - `WorkspaceOptions.openCamera?: string` and `WorkspaceOptions.onOpenCameraChange?: (camera: string | undefined, history: 'push' | 'replace') => void`.
  - Layout context fields `openCamera: string | undefined`, `onOpenCameraChange: (camera: string | undefined, history: 'push' | 'replace') => void` (no-op when the option is absent).
  - `CameraProjectionStrip` props `openCamera?: string`, `onOpenCameraChange?: (camera: string | undefined, history: 'push' | 'replace') => void`.

- [ ] **Step 1: Write failing strip tests:**
  - clicking tile "Enlarge CAM_B" calls `onOpenCameraChange('CAM_B', 'push')`.
  - with `openCamera='CAM_B'`, one dialog is shown with `· 2 / 3`; clicking "Next camera" calls `onOpenCameraChange('CAM_C', 'replace')`; next from the last wraps to the first.
  - closing the dialog calls `onOpenCameraChange(undefined, 'replace')`.
  - `closes when the open camera is deselected`: rerender with `selectedChannelIds` lacking CAM_B → `onOpenCameraChange(undefined, 'replace')`.
  - `keeps the open camera while channels are loading`: `cameraChannels=[]`, `openCamera='CAM_B'` → `onOpenCameraChange` not called.
  - with one selected camera, prev/next are disabled.
- [ ] **Step 2: Run** `npx vitest run src/lib/components/PointCloudLabelingWorkspace/CameraProjectionStrip` → FAIL.
- [ ] **Step 3: Implement the strip.** `selectedNames` = filtered channel names in strip order. Render one `CameraProjectionDialog` after the tile row (outside `{#if !collapsed}`, so it still opens with the strip collapsed), `open={openCamera !== undefined && selectedNames.includes(openCamera)}`, `onOpenChange` → `onOpenCameraChange(undefined, 'replace')` when closed. Frame data for the open camera: call `useCameraFrame(() => ({ ...same args as its tile }))` for the open channel; image `fullFrameUrl ?? frameUrl`. It follows `seqNumber`, so playback updates the image. Invalid-camera effect: when `summaryCameraChannels.length > 0` and `openCamera` is set and not in `selectedNames`, call `onOpenCameraChange(undefined, 'replace')`. Frames call `onEnlarge` → `onOpenCameraChange(name, 'push')`.
- [ ] **Step 4: Add the `1`–`9` shortcut.** In `CameraProjectionStrip`, `<svelte:window onkeydown>`: `getCameraForDigit(event, selectedNames)`; on a match `preventDefault` and `onOpenCameraChange(name, openCamera ? 'replace' : 'push')`. Test: pressing `2` on `document.body` opens CAM_B; pressing `2` in an `<input>` does nothing.
- [ ] **Step 5: Plumb through the workspace.** Add the two options to `WorkspaceOptions`, expose them in the layout context from `createWorkspaceController`, and pass `layout.openCamera` / `layout.onOpenCameraChange` in `PointCloudWorkspaceMainColumn`.
- [ ] **Step 6: Run** strip, frame and `PointCloudLabelingWorkspace.test.ts` tests → PASS.
- [ ] **Step 7: Commit** `feat: switch cameras in one enlarged camera dialog`.

### Task 5: Route keeps `camera` in the hash

**Files:**
- Rename: `routes/datasets/[dataset_id]/[collection_type]/[collection_id]/mcap-sequences/[sequence_id]/getTickNumberFromHash.ts` → `sequenceHash.ts` (and its test → `sequenceHash.test.ts`)
- Modify: same folder `+page.svelte`
- Test: same folder `sequenceHash.test.ts`, `page.test.ts`

**Interfaces:**
- Produces (`sequenceHash.ts`): `getTickNumberFromHash(hash: string): number` (unchanged), `getCameraFromHash(hash: string): string | undefined`, `buildSequenceHash(state: { tick: number; camera?: string }): string` — returns `tick=<n>` or `tick=<n>&camera=<encoded>`, no leading `#`.
- Consumes: `WorkspaceOptions.openCamera` / `onOpenCameraChange` (Task 4).

- [ ] **Step 1: Write failing helper tests:** `getCameraFromHash('#tick=3&camera=CAM_FRONT') === 'CAM_FRONT'`; `getCameraFromHash('#tick=3') === undefined`; `getCameraFromHash('#camera=') === undefined`; round trip with a name containing `/` and space; `buildSequenceHash({ tick: 4 }) === 'tick=4'`.
- [ ] **Step 2: Write failing route tests** (`page.test.ts`, mock `goto` like the existing tests):
  - loading with `#tick=2&camera=CAM_B` passes `openCamera='CAM_B'` to the workspace.
  - `onOpenCameraChange('CAM_B','push')` → `goto` with hash `tick=<t>&camera=CAM_B` and `replaceState: false`; `'replace'` → `replaceState: true`.
  - `keeps camera when tick changes right after a switch`: call `onOpenCameraChange('CAM_C','replace')` then `onTickChange(5)` without updating `page.url` → last `goto` hash is `tick=5&camera=CAM_C`.
  - `closing after switches pops a single history entry`: push open, two replaces, then `onOpenCameraChange(undefined,'replace')` → `history.back()` called once, no `goto` for the close.
  - closing a camera that came from the initial URL (no push in this page session) → `goto` with `replaceState: true` and hash `tick=<t>`.
- [ ] **Step 3: Run** `npx vitest run "src/routes/datasets/[dataset_id]/[collection_type]/[collection_id]/mcap-sequences/[sequence_id]"` → FAIL.
- [ ] **Step 4: Implement `+page.svelte`.** State: `let openCamera = $state(getCameraFromHash(page.url.hash))`, `let currentTick = $state(getTickNumberFromHash(page.url.hash))`, `let pushedCameraEntry = $state(false)`. A single `writeHash(history: 'push' | 'replace')` builds the URL from `buildSequenceHash({ tick: currentTick, camera: openCamera })` and calls `goto(url, { replaceState: history === 'replace', noScroll: true, keepFocus: true, state: page.state })`. `updateTickNumber(n)`: set `currentTick`, `writeHash('replace')`. `setOpenCamera(camera, history)`: when closing with `pushedCameraEntry` true → set `openCamera = undefined`, `pushedCameraEntry = false`, `history.back()`; otherwise set `openCamera`, set `pushedCameraEntry ||= history === 'push'`, `writeHash(history)`. `afterNavigate(({ type }) => { if (type === 'popstate') { openCamera = getCameraFromHash(page.url.hash); currentTick = getTickNumberFromHash(page.url.hash); pushedCameraEntry = false; } })`. Pass `tickNumber={currentTick}`, `openCamera`, `onOpenCameraChange={setOpenCamera}` to the workspace. Reset `openCamera`/`currentTick` when `sequenceId` changes (`goToSequence` drops the hash).
- [ ] **Step 5: Run** the route tests → PASS.
- [ ] **Step 6: Commit** `feat: keep the open camera in the point cloud URL`.

### Task 6: Changelog, checks, manual verification

**Files:**
- Modify: `CHANGELOG.md` (`## [Unreleased]` → `### Added`)

- [ ] **Step 1: Add the changelog entry** (load the `changelog` skill): `- Switch cameras in the enlarged camera view of the point cloud workspace with [ and ] (configurable in Settings → Shortcuts) or Shift + ← / →, also during playback. Press 1–9 to open camera N. The open camera is kept in the URL.`
- [ ] **Step 2: Run** `cd lightly_studio_view && make static-checks && make test` → clean/PASS. Run `cd lightly_studio && make static-checks && uv run pytest tests/resolvers/test_settings_resolver.py tests/api` (settings route tests) → PASS.
- [ ] **Step 3: Manual check in the dev server** with an MCAP dataset: open a camera, press `]` ×N during playback (playback keeps running, image follows tick), reload (dialog reopens on same camera and tick), Back (dialog closes in one step), remap next camera in Settings and use the new key.
- [ ] **Step 4: Commit** `docs: changelog entry for camera switch shortcuts`.
