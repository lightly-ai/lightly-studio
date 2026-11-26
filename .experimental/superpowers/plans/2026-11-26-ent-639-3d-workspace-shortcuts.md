# ENT-639: 3D workspace shortcuts and the shortcuts list

Linear: https://linear.app/lightly/issue/ENT-639

## What the code does today

- **Tool rail** (`PointCloudLabelingWorkspace/ToolRail/ToolRail.svelte`) has only two tools:
  `select` and `create-cuboid` (`WorkspaceTool` in `domain/contracts.ts`). Create has a
  hard-coded `shortcut: 'c'`; Select has none.
  - The issue lists Move / Rotate / Resize as tools, but they are not tools any more. They are
    gizmo handles on the selected cuboid (`CuboidGizmo.svelte`, `CuboidFaceResize`). They get no
    tool shortcut.
- **`Toolbar`** (`ui/toolbar/Toolbar.svelte`) already handles `shortcut` per item. It skips
  repeats, modifier keys, and text inputs, and shows the key in the tooltip
  (`ToolbarTooltip`). It also has a `shouldHandleShortcut` hook.
- **Fixed 3D keys** live in separate window listeners:
  - Space: `useWorkspacePlayback.handleWindowKeydown`
  - ←/→: `useSceneViewport`
  - W/A/S/D: `SceneViewport/sceneNavigationInput.ts`
  - Escape: `useCuboidDraft`, `useOrthographicDrag`, `useCuboidFaceResize`, `cuboidSelection.ts`
  - Enter: `useAnnotationDetailsEditing`
  - Ctrl/Cmd + wheel: `FrameTimeline/TimelineContent`
  - `e` (edit mode): the global `Header.svelte` handler through `settingsStore.key_toggle_edit_mode`
- **Delete**: `useWorkspaceEditing.handleDeleteCuboid(cuboidId)` exists (it is used by the panel
  and supports undo), but no key triggers it.
- **Configurable shortcuts are stored in the backend**: `models/settings.py`
  (`SettingBase` / `SettingDefaults`), `resolvers/settings_resolver.py`, an Alembic migration,
  the generated client, `hooks/useSettings.ts` defaults, and
  `Settings/settingsDialogState.svelte.ts` and `settingsDialogConfig.ts`.
- **Your PR #3565 (ENT-638, in review)** already adds `key_previous_camera` / `key_next_camera`
  with a migration, a `pointCloudShortcuts` group, and `staticPointCloudShortcuts`
  (Shift+←/→, 1–9). This branch builds on it. Keys already taken in 3D: Space, arrows,
  W/A/S/D, `e`, `[`, `]`, `1`–`9`.

## Decisions

1. **New settings keys only for the 3D tools.** The 2D Selection default is `s`, which clashes
   with W/A/S/D, so the 3D tools can't share the 2D keys.
   - `key_point_cloud_select`, default `q`
   - `key_point_cloud_create_cuboid`, default `c` (the key it has today)
2. **Delete / Backspace stay fixed** and are listed as a static row. They work only in edit mode,
   with a cuboid selected, and not while typing.
3. **Clash guard:** the tool rail passes `shouldHandleShortcut` to skip W/A/S/D. If a user
   records `w` as a tool key, navigation still wins. (Optional: warn in the settings dialog when
   a recorded 3D key is reserved. Not part of the first cut.)
4. **The `?` shortcut and header button are left out** for now. The issue marks them optional,
   and the rest of the app only has the menu entry. Easy to add later.

## Steps

### PR 1: configurable tool keys and Delete (backend + workspace)

1. **Backend**
   - Add `key_point_cloud_select` and `key_point_cloud_create_cuboid` to `SettingBase` and
     `SettingDefaults` (`models/settings.py`) and to `settings_resolver.set_settings`.
   - Alembic migration with `server_default` `q` / `c`, chained after the #3565 migration.
   - Update the backend settings tests. Regenerate the frontend client.
2. **Frontend defaults:** add the two keys to `hooks/useSettings.ts`.
3. **ToolRail**
   - Read the keys from `settingsStore`.
   - Set `shortcut` on Select and Create (the tooltips then show them).
   - Pass `shouldHandleShortcut` that ignores W/A/S/D.
   - Tests: the key switches the tool, typing in an input doesn't, W doesn't, the tooltip shows
     the key.
4. **Delete the selected cuboid**
   - Add a small hook `useDeleteSelectedCuboidShortcut` (in `useWorkspaceEditing/` or its own
     folder). It listens for Delete/Backspace and does nothing for repeats, modifier keys, text
     inputs, open dialogs, outside edit mode, or with no selection. Otherwise it calls
     `editing.handleDeleteCuboid(selectedCuboidId)` and prevents the default.
   - Wire it in `createWorkspaceController` (or `PointCloudLabelingWorkspace.svelte`).
   - Tests: it deletes in edit mode; it does nothing outside edit mode, with no selection, or
     inside an input.

### PR 2: the shortcuts list (Settings → Shortcuts)

5. **`settingsDialogConfig.ts`:** sections General, Image annotation, Point cloud.
   - **General:** Hide annotations, Toggle edit mode, Go back (Escape).
   - **Image annotation:** the current tool keys + Brush size.
   - **Point cloud, recordable:** Select, Create cuboid, Previous / next camera (from #3565).
   - **Point cloud, static:**
     - Play / pause: Space
     - Previous / next tick: ← / →
     - Move camera: W / A / S / D
     - Cancel or deselect: Escape
     - Confirm geometry field: Enter
     - Zoom timeline: Ctrl/Cmd + wheel
     - Delete selected cuboid: Delete / Backspace
     - Previous / next camera (alt): Shift + ← / →
     - Open camera 1–9: 1–9
   - Use "⌘" or "Ctrl" depending on the platform if a helper exists. Otherwise show
     "Ctrl/Cmd".
6. **`settingsDialogState.svelte.ts`:** add the two keys to the state, the form mapping, and the
   save payload.
7. **`ShortcutsTab.svelte`:** render the three groups. Update `SettingsDialog.test.ts` and
   `settingsDialogState.test.ts`.
8. **Remove the stale `'c'` hard-code** in `ToolRail` if PR 1 has not already done it.
9. **Changelog entry:** "Added keyboard shortcuts for the 3D tools and listed all point cloud
   shortcuts in Settings → Shortcuts."

If both PRs together stay under the Fast Track limit, merge them into one.

## Check against the acceptance criteria

- **Every point cloud shortcut is listed:** go through the listeners above against the Point
  cloud section.
- **No clash with W/A/S/D, nothing fires while typing:** the guard in step 3 and the tests in
  steps 3 and 4.
- **Validation:**
  - `cd lightly_studio && make static-checks && uv run pytest tests/…settings…`
  - `cd lightly_studio_view && make static-checks && make test`
  - Manual check in the workspace with the dev server.

## Open questions

- Default for Select: `q`, or another key? (`v` is the 2D "Hide annotations" key; `s` clashes
  with navigation.)
- Stack this branch on #3565 now, or wait for it to merge?
- One PR or the two-PR split above?
