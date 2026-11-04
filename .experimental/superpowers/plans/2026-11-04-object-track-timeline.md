# Object track timeline implementation plan

## Objective

Rebuild object track timeline support incrementally, with each stage usable and
reviewable on its own. Separate displaying annotation coverage from creating
annotations by extending that coverage.

Reuse the existing playback, tick navigation, buffering, object track identifiers,
and cuboid editing flows.

## Reference implementation

Use `kondrat-lig-11157-object-track-timeline` as the source branch. Reviewed source
tip: `11a72906a` (`Match track timeline names and colors to annotation classes`).
The implementation destination at review time is
`kondrat-lig-11157-object-track-timeline.implementation`.

The source branch contains these functional commits:

- `0f2757303`: read-only track query and timeline, consecutive runs, and keyframe
  navigation.
- `e4fc67f8b`: managed track persistence, starting a track from an existing cuboid,
  and adding a later keyframe with hold or interpolation between keyframes.
- `11a72906a`: track names and colors derived from annotation classes.

Port selected parts in the stages below rather than cherry-picking the complete
feature. The source combines behaviors that belong to separate milestones.

### Reusable source files

Paths below are relative to the repository root, on the source branch.

| Area | Source files | Destination stage |
| --- | --- | --- |
| Track read API | `lightly_studio/src/lightly_studio/models/mcap_sequence_tracks.py`, `api/routes/mcap_sequences/get_sequence_tracks.py` and `services/recording_service/get_sequence_tracks.py` under the same package | 2 |
| Timeline fetching and rendering | `lightly_studio_view/src/lib/components/PointCloudLabelingWorkspace/FrameTimeline/useSequenceTracks.svelte.ts` and `TrackTimelineRows/TrackTimelineRows.svelte` | 2, with grouped bars deferred to 3 |
| Consecutive runs | `TrackTimelineRows/buildTrackTimeline.ts` under the same timeline folder | 3 |
| Track creation and keyframe filling | `lightly_studio/src/lightly_studio/api/routes/mcap_sequences/edit_sequence_track.py` and `services/recording_service/edit_sequence_track.py` | Split between 4 and 5 |
| Managed track schema | `lightly_studio/src/lightly_studio/models/annotation/object_track.py` and migration `1793664000_81fa9b774c20_add_managed_object_tracks.py` | 4, only if the managed-track distinction is retained |
| Editing controls and mutations | `TrackEditingControls.svelte` and `useTrackEditing.svelte.ts` under the timeline folder | Adapt for 4 and 5 |

### Gaps to address while porting

- Track rows reserve a label gutter, while the existing ruler spans the available
  width. Share the gutter and tick geometry across both instead of copying this
  layout unchanged. The source calculates the current tick index but does not
  render a playhead through the track rows.
- Track selection is stored separately in the row component and its parent.
  Establish one selection owner and synchronize it with cuboid selection.
- The track read API scopes by sequence and dataset but does not filter by
  annotation source or expose that source in its summary.
- The source creates a track from an already persisted cuboid. It does not
  atomically create a new cuboid and track together.
- The source fills between an existing last keyframe and a later selected cuboid.
  It does not support dragging bar handles or extending coverage before the first
  keyframe.
- Matching coordinate frame IDs alone does not account for sensor motion across
  timestamps. Define the propagation frame and transforms explicitly.
- The source allows extension only for managed tracks. Decide whether this
  restriction belongs in the new feature; do not silently make existing tracks
  read-only in the new workflow.

## Stage 1: Define contracts and implementation boundaries

Establish these rules before implementing the UI:

- An object track identifies one object across ticks.
- An annotation belongs to a particular tick and annotation source.
- A timeline bar represents annotation coverage. It is derived from annotations,
  rather than persisted as a separate object.
- Playback, ruler, annotation markers, and bars share the same tick positions.
- Resolve sparse sequence numbers through the ordered tick list, as playback
  already does.
- Load sequence-wide coverage independently of which frames are buffered.
- Distinguish authored and generated annotations. The source uses the existing
  cuboid `interpolated` flag for generated annotations, including hold mode.
  Verify that this meaning remains suitable before reusing it.
- Define the first editing milestone as editing the selected annotation at one
  tick. Changes across a range belong to stage 5.

For this plan, “projected annotations” means propagating a cuboid across ticks.
Confirm the geometry policy before implementing stage 5.

**Deliverable:** a small data contract and a stack of focused implementation
changes. Split backend contracts, persistence, and frontend integration into
separate changes where this improves reviewability.

## Stage 2: Existing tracks aligned with playback

Start with one row per existing track and separate markers for its annotations.

### Implementation

- Add a lightweight sequence-level query for track coverage, scoped by sequence
  and annotation source. Avoid loading every tick's full scene.
- Give the ruler and track rows a shared horizontal axis.
- Reserve the same label gutter and inner padding for the ruler, buffering
  indicators, rows, and playhead. Use a common tick-position calculation.
- Extend the playhead through all track rows.
- Clicking an annotation marker seeks to its tick and selects the annotation.
- Selecting a cuboid highlights its track.
- Keep selected track and annotation state in the workspace editing context;
  reset it appropriately when changing sequences or annotation sources.
- Reuse annotation class names and colors consistently with the scene.
- In editing mode, reuse the existing cuboid editing flow for the selected
  annotation. Initially, edits affect that tick only.
- Keep seeking and selection distinct from mutation.

### Acceptance criteria

- Playback, stepping, scrubbing, and selection agree on the active tick.
- Existing annotation edits persist after reload.
- Coverage remains correct for unbuffered ticks and sparse sequence numbers.
- The first, middle, and last tick align across the ruler and rows at different
  viewport widths, including when the track list scrolls.

### Scope boundary

New tracks, grouped bars, and range propagation belong to later stages.

## Stage 3: Combine consecutive annotations into bars

Replace adjacent markers belonging to the same track with a continuous bar.

For example, annotations at ticks `1, 2, 3, 6, 7` become two bars: `[1–3]` and
`[6–7]`, assuming those numbers are consecutive entries in the sequence tick list.

### Implementation

- Determine adjacency from the ordered sequence ticks.
- Preserve gaps where annotations are missing.
- Keep annotation sources separate.
- Clicking within a bar resolves to the annotation at that tick.
- Derive bars from annotations without adding a separate persistence model.
- Preserve authored/generated distinctions within continuous coverage. The source
  splits runs when `interpolated` changes; retain that distinction visually while
  presenting the complete coverage of the track.
- Initially retain one row per track.

If grouping also means placing different, non-overlapping tracks on a shared row,
implement that as a separate layout change. Preserve each track's identity and
selection behavior.

### Acceptance criteria

- Bars accurately show coverage, including gaps.
- Bars regroup correctly after annotations change.
- Selection within a bar seeks to the correct tick and annotation.

## Stage 4: Add new tracks in editing mode

Add an **Add object track** action that starts a concrete creation flow.

### Implementation

1. Choose an annotation class and annotation source.
2. Create the first cuboid at the active tick using the existing interaction.
3. Persist the track and its first annotation atomically.
4. Select the new annotation and display its timeline row immediately.

Allocate track identifiers on the backend. Canceling creation must leave no empty
track, and failed creation must leave no orphaned data.

Also reuse the source's **Start track from selected cuboid** flow as a focused
substep: atomically create the track and attach the existing untracked cuboid.
Keep that endpoint distinct from creating a new cuboid and track together. For
the latter, reuse existing geometry validation but keep both writes in one
transaction. Handle retries and concurrent track-number allocation explicitly;
the source's dataset maximum plus one calculation is not sufficient on its own
for concurrent requests.

If managed-track ownership is retained, introduce its schema migration in this
stage rather than making read-only rendering depend on it. Validate the migration
for PostgreSQL and schema creation for DuckDB.

### Acceptance criteria

- The new track survives reload and appears at the correct tick.
- Track creation is available in editing mode.
- Canceled and failed creation leave no orphaned track or annotation.

## Stage 5: Extend annotation coverage across ticks

This is the first stage where dragging a timeline bar creates data.

### Interaction and persistence

- Add start and end handles in editing mode.
- Pause playback during the interaction.
- Snap handles to ticks and preview the proposed coverage.
- On release, submit one backend operation that creates annotations on newly
  covered ticks.
- Preserve existing annotations and prevent duplicates on request retries.
- Save the operation atomically.
- Refresh affected timeline and scene caches after persistence.
- Invalidate affected prefetched tick details as well as the active tick, so
  playback cannot reuse stale annotation data.
- Validate sequence, dataset, annotation source, track membership, target ticks,
  and coordinate transforms on the backend.

For example, extending `[10–15]` to `[10–20]` creates annotations at ticks
`16–20`, retaining the same track identity.

### Geometry policy

Recommended initial behavior: copy the boundary cuboid in a defined coordinate
frame, applying the required transforms for each target tick. Account for sensor
motion explicitly. Establish the coordinate frame and behavior for unavailable
transforms before implementing propagation.

Interpolation between edited keyframes can follow as a separate change.

The source already implements hold and interpolation between two authored
keyframes, including quaternion interpolation and timestamp-based fractions with
a tick-index fallback. Reuse those calculations only after the coordinate-frame
policy is established. Keep the operations distinct:

- Extending a bar into uncovered ticks needs a boundary cuboid and target range;
  it must not require a second, already-created annotation.
- Filling between two authored keyframes can use the source's keyframe endpoint
  as a separate follow-up.

Place database queries and inserts in resolvers, with services coordinating the
operation and transaction. Split the source's combined service accordingly.

### Scope boundary

Start with outward extension only. Shortening a bar deletes annotations, while
moving the whole bar relocates coverage. Define and implement those behaviors in
separate changes.

### Acceptance criteria

- Preview and persisted coverage match.
- Generated annotations have correct geometry and track identity.
- Existing annotation edits are preserved.
- Retrying an operation does not create duplicates.
- A failed operation leaves coverage unchanged.

## Validation

Cover behavior at the appropriate layer:

- Empty sequences and sparse ticks.
- Sequence and annotation source filtering.
- Playback, scrubbing, and selection synchronization.
- Consecutive coverage and gaps.
- Creation cancellation and failure.
- Concurrent creation, request retries, and existing tracked cuboid rejection.
- Range extension, retries, and atomic failure.
- Authored/generated distinctions and preservation of existing annotations.
- Annotation cache invalidation during subsequent playback.
- Coordinate transforms, including sensor motion and unavailable transforms.

For frontend changes, activate the Node version in `lightly_studio_view/.nvmrc`,
then run `make static-checks` and `make test` from `lightly_studio_view`.

For backend changes, run `make static-checks` and
`uv run pytest <affected_tests>` from `lightly_studio`. Avoid rebuilding the
frontend unless required. Regenerate the API schema and frontend client when
changing API contracts.

Include screenshots or recordings with UI pull requests.

Review the source tests as fixtures and behavior references, then add coverage
for the gaps above. In particular, the source's row tests do not replace visual
verification of alignment with the playback ruler. Keep Svelte components under
the frontend guideline's 100-line target and follow the hook folder conventions
while splitting the port into focused changes.

## First implementation milestone

Complete stages 1 and 2: existing tracks are visible, selectable, and editable at
the active tick, synchronized with playback. Continue with grouping, creation,
and propagation as successive milestones.
