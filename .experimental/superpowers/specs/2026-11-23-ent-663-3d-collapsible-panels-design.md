# ENT-663: Collapsible panels in the 3D annotation workspace

Linear: https://linear.app/lightly/issue/ENT-663

## Intent

In the 3D (point cloud) annotation workspace, labeling happens in the 3D scene. The panels
around it (orthographic views, right side panel, camera strip, frame timeline) take a lot of
the screen. Users must be able to collapse each of them, so the 3D scene can fill almost the
whole workspace, and bring each back with one click.

## Goals

- Every panel around the 3D scene can be collapsed to a slim bar and expanded again.
- Collapse/expand controls look the same and sit in the same place on every panel.
- Collapsed state is remembered per panel across frames, sequences and reloads.
- The 3D scene resizes smoothly when panels change: no distortion, camera pose kept.
- Focus mode: one toggle that collapses all panels and restores the previous layout.
- Keyboard shortcuts for focus mode and for stepping frames.

## Non-goals

- Panels in the 2D image and video views (STU-33, LIG-11580).
- Moving panels to another side (STU-148).
- Remembering panel *sizes* across reloads (only collapsed state is required).

## Anti-goals

- A collapsed panel that still renders WebGL views in the background.
- Frame navigation becoming impossible while the timeline is collapsed.
- Breaking the existing camera strip behavior.

## Approaches considered

- **A. Paneforge for everything (chosen by Kondrat).** The frame timeline becomes a pane in
  the main column's vertical `PaneGroup`, the scene's perspective/orthographic split becomes a
  nested `PaneGroup`, and the right side panel becomes collapsible. One generic hook drives
  every collapsible pane. Uniform: every panel resizes, and dragging a divider to the edge
  collapses it. Cost: the timeline's content-driven height and its own track-rows resizer give
  way to the pane divider.
- **B. Hybrid.** Paneforge only for the orthographic split and right panel; the timeline keeps
  its content height and a collapsed flag. Less churn in the timeline, but two collapse
  mechanisms.
- **C. Show/hide only.** No resizing of the orthographic strip, which the issue asks for.
  Dropped.

## Design

### Shared building blocks

- **`useCollapsiblePane(storageKey, defaultCollapsed)`**: generalize `useCameraPane` (same file
  pattern, `useSessionStorage` for the collapsed flag, `$effect` syncing the flag to the
  `PaneAPI`, `toggle`, `setCollapsed`, bound `pane`). `useCameraPane` is replaced by it; keep
  the camera strip's existing storage key so users keep their setting.
- **`PanelCollapseButton`**: one ghost icon button (chevron, `size: 'xs'`, `h-7 w-7 p-0`, like
  the camera strip's) with the aria labels "Collapse <panel>" / "Expand <panel>". The chevron
  points in the direction the panel will move. Every panel uses it, at the right end of its
  header row (top end of its bar for the right panel).
- **Pixel collapsed sizes**: paneforge 1.0.2 sizes are percentages. A collapsed bar should be
  exactly one header high (or one bar wide), so collapsed and minimum sizes are computed from
  the measured `PaneGroup` size (ResizeObserver) and passed as percentages. If paneforge does
  not react to a changing `collapsedSize`, the builder may fall back to a fixed percentage
  (today's camera strip uses `collapsedSize={4}`).

### Panels

1. **Orthographic views strip** (`PointCloudWorkspaceScene.svelte`): the `flex-[3]` /
   `flex-[2]` divs become a vertical `PaneGroup`: perspective pane (about 60%) and a
   collapsible orthographic pane (about 40%), with a `PaneResizer` styled like the existing
   ones. The orthographic pane gets a header "Orthographic views" with the collapse button.
   Collapsed, it shows only that header and **unmounts** the three viewports.
   - This replaces the "show orthographic views" checkbox in `SceneViewSettings`: remove the
     checkbox; `showOrthographicViews` becomes "orthographic pane is expanded". Default stays
     collapsed (today's default is off). Reuse the
     `lightlyStudio_pointCloudShowOrthographicViews` storage key or migrate it, builder's call.
   - The per-view expand buttons (`scene.expandedProjection`) keep working. When one view is
     expanded, the other views stay mounted and hidden, as today, so cameras keep their pose
     (builder's call from the review).
2. **Right side panel** (`WorkspacePanels.svelte`): the 22% pane becomes `collapsible`.
   Collapsed, it is a slim vertical bar (one button wide) with the expand button at the top
   and the tooltip "Show side panel". The collapse button sits at the top right of the
   expanded panel.
3. **Camera strip**: unchanged behavior, moved onto `useCollapsiblePane` and
   `PanelCollapseButton`.
4. **Frame timeline** (`PointCloudWorkspaceMainColumn.svelte`, `FrameTimeline`): becomes the
   third pane of the main column's vertical `PaneGroup` (scene / camera strip / timeline),
   collapsible, with a resizer above it.
   - Collapsed: a slim bar with the title "Timeline" and the expand button, nothing else.
   - Expanded: the transport row, then the tracks and frame tags filling the rest of the pane
     with scrolling. The collapse button sits at the right end of the transport row.
   - The pane divider replaces `TrackRowsResizer` and `useTrackRowsHeight`; remove both.
   - The default timeline size should roughly match today's default (transport row plus 160px
     of track rows).

### Who opens panels

- Only the user collapses or expands panels (button, divider drag, shortcut, focus mode). The
  app never opens a collapsed panel by itself, including on cuboid selection or while "Add
  track" is armed. Moving and resizing cuboids works in the scene without the side panel.

### Focus mode

- A button in `WorkspaceHeader`, next to fullscreen, labeled "Focus on 3D scene" /
  "Exit focus".
- Entering saves which of the four panels are expanded, then collapses all of them. Exiting
  expands the saved ones.
- Expanding any panel by hand while in focus mode leaves focus mode (the snapshot is dropped,
  other panels stay as they are).
- Focus mode itself is not persisted; the panels' collapsed flags are.
- The camera strip chevron in `WorkspaceHeader` is removed: the strip has its own button, and
  the header holds workspace-wide controls only.

### Keyboard shortcuts

- Step to the previous / next frame: `,` / `.` (global, through
  `useWorkspacePlayback.handleWindowKeydown`, like Space). Needed because a collapsed timeline
  has no step buttons.
- Toggle focus mode: a single key, builder picks one that is free.
- Shortcuts are ignored while typing in an input, textarea, select or contenteditable, and
  while a dialog is open. The builder checks for conflicts with the existing workspace keys
  (Space, Escape, Enter, arrows, scene navigation letters such as `A`).
- Per-panel toggle shortcuts are out of scope.

### 3D scene resizing

- `usePointCloudCamera` already observes canvas size (`refitCameraToViewport`). The builder
  verifies that collapsing/expanding any panel keeps the perspective camera pose and only
  updates aspect ratio, for both perspective and orthographic views, and fixes it if not.
- `usePointCloudCamera` lives in `PointCloudViewer/` and is shared with the other point cloud
  viewer, so any fix there is tested in both places.

## Left to the builder

- Exact default pane sizes and min/max sizes.
- Icons (chevron directions, focus icon) and tooltip wording beyond the labels above.
- Storage key names for the new panels (follow `lightlyStudio_pointCloud*`).
- Test split between unit tests (hooks) and component/story tests; update the workspace
  stories so every panel's collapsed state can be seen.
