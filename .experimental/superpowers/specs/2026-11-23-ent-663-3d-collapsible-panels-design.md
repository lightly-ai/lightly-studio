# ENT-663: Hideable panels in the 3D annotation workspace

Linear: https://linear.app/lightly/issue/ENT-663

## Intent

In the 3D (point cloud) annotation workspace, labeling happens in the 3D scene. The panels
around it (orthographic views, details side panel, camera strip, frame timeline) take a lot of
the screen. Users must be able to hide each of them entirely, so the 3D scene can fill almost
the whole workspace, and bring each back with one click.

## Decision: header toggle controls

Icons in the workspace header show and hide the panels, like the layout controls of Xcode,
Claude desktop and VS Code. A hidden panel leaves no bar behind: the 3D scene gets the space.
This replaces the earlier idea of collapsing each panel to a slim bar with a chevron.

## Goals

- One icon toggle per panel in `WorkspaceHeader`, highlighted while the panel shows: orthographic
  views, camera strip, object tracks, frame tag tracks, right side panel.
- Every panel also has an X button in its own header that hides it.
- Every panel uses one template: title on the left, actions and the X on the right.
- The shown/hidden state is remembered per panel across frames, sequences and reloads.
- The 3D scene resizes smoothly when panels change: no distortion, camera pose kept.
- Focus mode: one toggle that hides all panels and restores the previous layout.
- Keyboard shortcuts for focus mode and for stepping frames.

## Non-goals

- Panels in the 2D image and video views (STU-33, LIG-11580).
- Moving panels to another side (STU-148).
- Remembering panel *sizes* across reloads (only the shown state is required).

## Anti-goals

- A hidden panel that still renders WebGL views in the background.
- Frame navigation becoming impossible while the timeline is hidden.
- Breaking the existing camera strip behavior.

## Design

### Shared building blocks

- **`WorkspaceLayoutToggles`**: a group of ghost icon buttons (`aria-pressed`, tooltip
  "Hide/Show <panel>"). It takes `toggles` (`id`, `label`, `icon`, `isActive`) and `onToggle`.
  `WorkspaceHeader` renders one for the panels and, after a divider, one for focus mode.
- **`useWorkspacePanes(storageKey)`**: generalizes `useCameraPane`. Owns the shown flag
  (`useSessionStorage`), syncs it to the paneforge `PaneAPI` (`collapse()` / `expand()`), and
  exposes `toggle`, `hide`, `isShown` and the bound `pane`. Hidden uses `collapsedSize={0}`.
  `useCameraPane` is replaced by it; keep the camera strip's storage key.
- **`WorkspacePanel`**: one template for every panel in the 3D workspace (it grows out of
  `WorkspacePanelHeader` and replaces it).
  - Header (`text-xs`, muted title, about 32px high): title left; an optional `actions`
    snippet, then the X button (`onHide`) at the far right.
  - Body is unmounted while the panel is hidden, so no viewport renders in the background.
  - A **section** inside a panel (Sequence tags, Frame tags, Annotations) uses
    the same template with `onToggle` and `collapsed`: it folds in place to its header with a
    chevron. Sections are not part of the header toggles.
  - Non-hideable use: the "3D scene" header has no X.
- **Pixel sizes**: paneforge 1.0.2 sizes are percentages, so default and minimum sizes are
  percentages. Double-clicking a resizer restores the panel's default size.

### Panels

1. **Orthographic views** (`PointCloudWorkspaceScene.svelte`): a horizontal split next to
   the perspective view (about 25%), hideable. The "show orthographic views" checkbox in
   `SceneViewSettings` is removed; the header toggle replaces it. Default stays hidden. The
   A settings button in the panel header switches the layout: views stacked beside the scene
   (dock right) or in a row below it (dock bottom). The choice is remembered like the panel's
   shown state. The per-view expand buttons keep working; other views stay mounted so cameras keep their pose.
2. **Right side panel** (`WorkspacePanels.svelte`): titled "Right side panel" in the prototype
   (builder picks the final name with the glossary skill), about 22%, (about 22%), hideable. Its
   sections become `WorkspacePanel` sections that fold in place and remember their state. The
   frame tags section keeps its `inert` stale wrapper. `Segment` and `SegmentTags` stay for the
   2D views; the 3D panel reuses the tag list body.
3. **Camera strip**: same behavior as today, on `useWorkspacePanes` and `WorkspacePanel`.
4. **Timeline** (`PointCloudWorkspaceMainColumn.svelte`, `FrameTimeline`): the bottom pane of
   the main column (about 26%). The timeline itself is not hideable: its header (transport
   controls in `actions`) and the frame ruler always stay, so frame navigation keeps working.
   Below the ruler sit two separate hideable panels, each with its own header toggle:
   - **Object tracks**: the track toolbar in its header actions, then the track rows.
   - **Frame tag tracks**: the tag rows.
   Hiding a panel removes it. With both hidden, the timeline pane shrinks to the compact height
   (header plus ruler); showing one restores the previous pane size. The pane divider replaces
   `TrackRowsResizer` and `useTrackRowsHeight`; remove both. The divider is hidden while
   both panels are hidden.

### Who shows panels

- Only the user shows or hides panels (header toggle, X, shortcut, focus mode). The app never
  shows a hidden panel by itself, including on cuboid selection or while "Add track" is armed.

### Focus mode

- A toggle next to the panel toggles in `WorkspaceHeader`: "Focus on 3D scene" / "Exit focus".
- Entering saves which panels are shown, then hides all of them. Exiting shows the saved ones.
- Showing any panel by hand while in focus mode leaves focus mode (the snapshot is dropped).
- Focus mode itself is not persisted; the panels' shown flags are.
- The camera strip chevron in `WorkspaceHeader` is replaced by the camera strip toggle.

### Keyboard shortcuts

- Previous / next frame: `,` / `.` (global, through `useWorkspacePlayback.handleWindowKeydown`,
  like Space). Needed because a hidden timeline has no step buttons.
- Toggle focus mode: a single free key the builder picks.
- Shortcuts are ignored while typing in an input, textarea, select or contenteditable, and
  while a dialog is open. Check conflicts with Space, Escape, Enter, arrows and scene keys.
- Per-panel toggle shortcuts are out of scope.

### 3D scene resizing

- `usePointCloudCamera` already observes canvas size (`refitCameraToViewport`). Verify that
  showing or hiding any panel keeps the perspective camera pose and only updates the aspect
  ratio, for perspective and orthographic views, and fix it if not.
- `usePointCloudCamera` is shared with the other point cloud viewer, so test any fix in both.

## Prototype

`WorkspaceLayout (prototype)` in Storybook (`WorkspacePanel/WorkspaceLayout.stories.svelte`)
shows the target layout: header toggles, X buttons, folding sections, and focus mode.

## Left to the builder

- Exact default pane sizes and min/max sizes.
- Icons for the toggles and tooltip wording beyond the labels above.
- Storage key names for the new panels (follow `lightlyStudio_pointCloud*`).
- Test split between unit tests (hooks) and component/story tests.
