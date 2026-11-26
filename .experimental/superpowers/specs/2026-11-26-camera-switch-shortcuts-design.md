# Switch cameras with keyboard shortcuts (ENT-638) — design

## Why

QA feedback: cameras are used constantly in the point cloud workspace, and switching between them
takes a close + click today. A user should step through all selected cameras without the mouse,
always see which camera is shown, and keep the open camera across a reload.

## Goals

- In the enlarged camera view: previous/next camera via `[` / `]` and Shift+←/→, plus
  previous/next buttons. Header shows `Camera: CAM_FRONT · 2 / 5`.
- In the workspace: `1`–`9` open camera N in strip order.
- The open camera is in the URL, so reload and shared links reopen it.
- Shortcuts never fire while typing in an input (geometry fields, class search, …).

## Non-goals

- Persisting the camera filter (selected cameras) in the URL.
- Making `1`–`9` or the Shift+←/→ alternates configurable (see "Configurable keys").

## Approaches considered

1. **Hash param next to `tick` (picked).** `#tick=12&camera=CAM_FRONT`. Same mechanism the route
   already uses for the tick, survives reload, no load re-run.
2. Nested route `…/[sequence_id]/cameras/[camera]`. Reload-safe, but every switch is a navigation
   that re-runs loads, splits hash handling across layout/page, and moves the workspace into a
   layout. Too much churn for a modal.
3. SvelteKit shallow routing (`pushState` + `page.state`). `page.state` is lost on reload, which
   is the thing we want to avoid.

## Design

**URL state (route page owns it, like `tick`).**

- `+page.svelte` reads `camera` from the hash and passes `openCamera?: string` and
  `onOpenCameraChange(name | undefined)` into `PointCloudLabelingWorkspace`.
- Value is the camera name (`group_component_name`), not `channel_id`: readable and meaningful
  in a shared link.
- Opening the dialog: `goto(url, { replaceState: false })` → one history entry, so browser Back
  closes the dialog. Switching camera while open and closing: `replaceState: true`, so stepping
  through 6 cameras does not leave 6 history entries.
- Hash parsing/writing goes into a small pure helper next to `getTickNumberFromHash`
  (read/write `tick` and `camera` without clobbering each other).
- Unknown or unselected camera in the URL → dialog stays closed and the param is dropped.
- `goToSequence` already drops the hash, so changing sequence closes the dialog.

**Single dialog, lifted up.**

- `CameraProjectionFrame` no longer owns a dialog or `isEnlarged`; its click calls
  `onEnlarge(channelName)`.
- `CameraProjectionStrip` renders one `CameraProjectionDialog` for the open camera, using the
  frame data of that camera (full frame URL, projection, annotations).
- Navigation order = selected cameras in strip order. Prev/next wrap around. With one selected
  camera, prev/next buttons are disabled and the keys do nothing.
- Pure helper `getAdjacentCamera(names, current, direction)` holds the wraparound logic so it can
  be unit-tested without the DOM.

**Keys.**

- Dialog `onkeydown` (already handles Space): previous-camera key (default `[`) / Shift+← =
  previous, next-camera key (default `]`) / Shift+→ = next.
- Workspace-level `1`–`9`: open camera N if it exists. Ignored with Alt/Ctrl/Meta and when the
  target is a text input (reuse `isTextInputTarget`).
- Ticket suggested `C` to open the last-used camera, but `C` is already "Create cuboid" in the
  point cloud tool rail. Dropped: `1` covers "open first camera"; no extra key.
- No conflict with Space, arrows (plain arrows stay for ticks; we use Shift+arrows), W/A/S/D, `e`.

## Playback

Camera switching works while the sequence plays (user requirement).

- Switching camera (keys, buttons, `1`–`9`) never pauses or restarts playback; Space in the
  dialog keeps toggling playback as today.
- The dialog image follows the current tick for the newly chosen camera.
- During playback `onTickChange` writes the hash on every tick. The route keeps `camera` in its own
  `$state` and builds the whole hash from `{ tick, camera }` on every write, instead of patching
  `page.url.hash`. A tick write right after a camera switch (or the reverse) cannot drop the
  other value, even before `page.url` has caught up.
- The single dialog stays mounted across ticks and camera switches (no close/open animation per
  switch).

## Configurable keys

Previous/next camera are recordable in Settings → Shortcuts, like the 2D tool keys.

- Backend: `key_previous_camera` (default `[`) and `key_next_camera` (default `]`) on
  `SettingBase` / `SettingDefaults` in `models/settings.py`, copied in
  `settings_resolver.py`, plus an Alembic migration adding both columns with server defaults.
  Regenerate the frontend API client.
- Frontend: add `keyPreviousCamera` / `keyNextCamera` to `ShortcutSettingKey`,
  `settingsDialogState.svelte.ts` (state, save mapping, defaults) and `useSettings.ts` defaults.
  New "Point cloud" group in `ShortcutsTab.svelte` with the two recordable rows, plus static rows
  "Previous / next camera (alt): Shift + ← / →" and "Open camera N: 1–9".
- The dialog reads the keys from `useSettings`, not hardcoded. Tooltips on the prev/next buttons
  show the configured key.
- `1`–`9` and Shift+←/→ stay fixed: a digit range does not fit the single-key recorder, and the
  arrows are an alternate binding.

**One PR** (user's decision): backend settings, migration, API client, Settings rows, and the
feature ship together.

## Tests

- Unit: `getAdjacentCamera` — wraparound at first/last, single camera, current not in list.
- Unit: hash helper — read/write `camera` keeps `tick` intact and vice versa.
- Component: dialog prev/next buttons + `[`/`]` switch camera and update the "2 / 5" header;
  keys ignored while focus is in an input.
- Route: reload with `#camera=…` opens the dialog; invalid name does not.
- Playback: switching camera while playing keeps playing; a tick change after a camera switch
  keeps `camera` in the URL.
- Backend: settings resolver round-trips the two new keys; defaults are `[` / `]`.
- Settings: the two rows record and save; a remapped key switches cameras in the dialog.

## Left to the builder

Exact placement of the `1`–`9` listener (workspace controller vs. strip), and button styling.
