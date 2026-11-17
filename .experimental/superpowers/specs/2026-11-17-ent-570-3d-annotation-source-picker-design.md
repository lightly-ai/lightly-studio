# ENT-570: Pick the annotation source for new cuboids in the 3D workspace

Linear: [ENT-570](https://linear.app/lightly/issue/ENT-570/make-annotation-collection-editable),
sub-issue of ENT-563 (3D labeling workflow).

## Why

New annotations go to the default `annotation` source and the user cannot change that. Gravis
adds model predictions to every MCAP file, so each sequence will have several sources: the
predictions and the labeler's own labels. Before a labeler draws a cuboid, they must be able to
say which source it goes to.

The 2D sample details view already does this (#3118–#3121). The 3D point cloud workspace does
not: `useCreateCuboidAnnotation` never sends `annotation_collection_name`, so every cuboid lands
in `annotation`.

## Goals

- In the 3D workspace, the user picks the source new cuboids go to.
- When the source is unknown at creation time, the create modal asks for it, next to the class.
- The user can switch the source at any time in the right panel and always sees the current
  target while drawing.
- The user can type a new source name; the source is created with the first cuboid.
- A cuboid that went to the wrong source is noticed at once (see "Mistakes").

## Non-goals (follow-up ticket)

- Copying a cuboid or track to another source.
- Moving a cuboid or track to another source.

Both must work per track (a track belongs to one source, so a tracked cuboid cannot move or be
copied alone). Both need a backend endpoint that handles all cuboids of a track in one
transaction and marks evaluation runs stale for both sources. They share that work, so they go
into one follow-up ticket: "Move/Copy track to source".

Also out of scope: read-only prediction sources, hiding sources in 3D (the 3D panel has no
source visibility), undo in the 3D workspace, and any backend change. `POST
/collections/{id}/annotations` already takes `annotation_collection_name` and creates the source
when it is missing.

## Anti-goals

- Coupling 2D and 3D. The 3D workspace must not import from `hooks/useAnnotationTarget` or
  depend on the 2D `AnnotationLabelContext`. Shared components may only get generic, optional
  extensions that 2D ignores.
- A cuboid silently landing in a source the user did not choose.

## Approaches

1. **3D-only wiring inside `PointCloudLabelingWorkspace` (chosen).** A small, self-contained
   target-source hook and a pure resolver live in the workspace folder. The panel, the viewport
   and the create modal use it. Same rules as 2D, no shared code with it.
2. Mount the 2D annotation label context in the 3D workspace and reuse `useAnnotationTarget`.
   Least new code, but it expects 2D `AnnotationView`s and hidden IDs, and couples the views.
   Rejected (anti-goal).
3. Source dropdown in the 3D toolbar only. Quickest UI, but the ticket asks for the right panel
   and it would behave differently from 2D. Rejected.

For the modal:

1. **Generic optional slot in the shared `SelectClassDialog` (chosen).** 3D passes its source
   picker in the slot; 2D passes nothing and is unchanged. Class list, class creation,
   permission gate and analytics stay in one place.
2. A separate 3D dialog. Fully separate, but duplicates all of the above. Rejected.

Kondrat picked approach 1 in both cases, with the constraint not to mix 2D and 3D, and decided
to handle wrong-source mistakes by visibility now and "Move/Copy track to source" later.

## Design

### Rules (pure function, `resolveCuboidTargetSource`)

Inputs: the remembered pick, a name typed on this page, the source names (undefined while
loading), and whether loading failed. Output: `{ targetSource, blockedReason }`.

- Picked source that exists → it.
- Typed name (not created yet) → it.
- Exactly one source → it, no pick needed.
- No sources → default `annotation` (what the backend creates anyway).
- Several sources, no valid pick → unresolved: "Pick where new annotations go."
- Loading → blocked: "Loading annotation sources…"; load error → blocked with the reload message.
- A remembered pick whose source disappeared (renamed or deleted elsewhere) is forgotten, so the
  next cuboid asks instead of re-creating the old name.

This duplicates a few lines of 2D's `resolveTargetSource` on purpose (anti-goal above). The
message strings are copied, not imported.

### State (`useCuboidTargetSource`, in `PointCloudLabelingWorkspace/`)

- Reads the sources the workspace already loads in `useWorkspaceSceneData`.
- Remembers the pick per source collection (`annotationSourceCollectionId`) in
  `useGlobalStorage().lastAnnotationSource`. This store is generic storage keyed by collection
  ID; 2D keys it by the image collection, 3D by its source collection, so the picks never mix.
- Exposes `targetSource`, `blockedReason`, `needsPick` (several sources, no pick),
  `setTarget(name, { isNew })`.
- Created once in the workspace controller and passed down, like the other workspace hooks.

### Creating a cuboid

`useCreateCuboidAnnotation` takes the target-source hook and sends the target as
`annotation_collection_name`. The flow when the user finishes drawing:

1. Loading or load error → toast with the reason, nothing is created.
2. Class remembered and source resolved → create directly, no modal (as today).
3. Class unknown, or source unresolved (`needsPick`) → open the create modal:
   - Class list as today. If a class is remembered, it is preselected.
   - Source section (3D only, via the slot): the sources of the sequence plus "New source…".
     The current target is preselected; with `needsPick` nothing is preselected.
   - Confirm needs both a class and a source. Confirm remembers both; Cancel creates nothing.
4. Success toast names the source: "Cuboid added to labels".
5. The new cuboid is selected (as today), so its row shows under its source group.

After the first cuboid creates a typed source, the source list is refetched so it shows up.

Tracks keep their own source: extending a track uses the track's source (already the case in
`useExtendSequenceTrack`), starting a track keeps the cuboid's source. The picked target only
applies to new standalone cuboids.

### `SelectClassDialog` extension (shared, generic)

- Optional `extra` snippet rendered below the class list.
- Optional `canConfirm` flag (default true) that, with a selected class, enables Confirm.
- Optional `initialLabel` to preselect a class.
- 2D call sites pass none of these and behave exactly as today.

### Right panel

- Each source group header in `PointCloudAnnotationList` gets a radio; the checked one is the
  target and the group is highlighted.
- Every source of the sequence is listed, including sources with no cuboids on the current tick
  ("No cuboids on this tick"). Today `groupAnnotationsBySource` skips empty sources; the picker
  needs all of them, also on an empty sequence.
- A "New source…" row with a text input below the groups sets a typed target.
- With `needsPick`, the panel shows "Pick where new annotations go." above the groups.

```
Annotations
  Pick where new annotations go.          (only while nothing is picked)
  ◉ labels          12 cuboids  ▾
  ○ gravis_preds    40 cuboids  ▾
  ○ gravis_v2       No cuboids on this tick
  + New source…
```

### Viewport chip

While the Create cuboid tool is active, a chip at the top of the viewport shows the target
("New cuboids go to labels"), or "Pick where new annotations go." in a warning color. The tool
rail is an icon column with no room for text, so the chip lives in the viewport.

Mockup (panel and chip; the modal is not in it yet): `ent-570-source-picker-mockup.html`,
shared in the ENT-570 session.

### Mistakes (wrong source)

Decision: make the mistake visible at once, fix by deleting.

- The chip shows the target the whole time the tool is on.
- The modal shows the source whenever it opens.
- The success toast names the source.
- The new cuboid is selected and listed under its source group.

So a mistake costs one or two cuboids, fixed by deleting and redrawing. A proper "Move to
source" is in the follow-up ticket (see Non-goals).

## Calls made by Claude (check these)

- Pick storage reuses `lastAnnotationSource`, keyed by the 3D source collection.
- Empty sources are shown in the panel.
- Viewport chip instead of a label in the tool rail.
- The modal preselects the remembered class and the current source.
- Loading or load error still blocks with a toast (no modal), as in 2D.
- Picking a source needs role labeler or higher and editing mode, the same gate as 2D.
- The 2D source radio and "New source" input are plain UI pieces; they move from
  `SampleDetails/` to a neutral `components/AnnotationSource/` folder and 3D reuses them, so the
  look matches and 3D never imports from `SampleDetails/`.

## Left to the builder

- Exact component split for the panel radio, the "New source…" row and the modal source section
  (one 3D source-list component can serve the modal and the "New source…" input).
- Tests: unit tests for the resolver and the hook; component tests for the panel, the modal slot
  (2D unchanged without it) and the chip; a test that `useCreateCuboidAnnotation` sends the
  name, opens the modal when the source is unresolved, and stops when loading or failed. Follow
  the frontend-guide, clean-code and glossary skills ("annotation source" is the user-facing
  term).
