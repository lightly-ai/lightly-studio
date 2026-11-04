# Object track timeline implementation plan

## Objective

Rebuild object track timeline support incrementally, with each stage usable and
reviewable on its own. Separate displaying annotation coverage from creating
annotations by extending that coverage.

Reuse the existing playback, tick navigation, buffering, object track identifiers,
and cuboid editing flows.

## Reference implementation

Use `kondrat-lig-11157-object-track-timeline` as a reference once the previous
implementation is located. At planning time, the local branch points to the same
commit as the working branch and exposes no additional diff. Locate the intended
reference before porting any changes; do not restore it wholesale.

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
- Extend the playhead through all track rows.
- Clicking an annotation marker seeks to its tick and selects the annotation.
- Selecting a cuboid highlights its track.
- In editing mode, reuse the existing cuboid editing flow for the selected
  annotation. Initially, edits affect that tick only.
- Keep seeking and selection distinct from mutation.

### Acceptance criteria

- Playback, stepping, scrubbing, and selection agree on the active tick.
- Existing annotation edits persist after reload.
- Coverage remains correct for unbuffered ticks and sparse sequence numbers.

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

For example, extending `[10–15]` to `[10–20]` creates annotations at ticks
`16–20`, retaining the same track identity.

### Geometry policy

Recommended initial behavior: copy the boundary cuboid in a defined coordinate
frame, applying the required transforms for each target tick. Account for sensor
motion explicitly. Establish the coordinate frame and behavior for unavailable
transforms before implementing propagation.

Interpolation between edited keyframes can follow as a separate change.

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
- Range extension, retries, and atomic failure.
- Coordinate transforms, including sensor motion and unavailable transforms.

For frontend changes, activate the Node version in `lightly_studio_view/.nvmrc`,
then run `make static-checks` and `make test` from `lightly_studio_view`.

For backend changes, run `make static-checks` and
`uv run pytest <affected_tests>` from `lightly_studio`. Avoid rebuilding the
frontend unless required. Regenerate the API schema and frontend client when
changing API contracts.

Include screenshots or recordings with UI pull requests.

## First implementation milestone

Complete stages 1 and 2: existing tracks are visible, selectable, and editable at
the active tick, synchronized with playback. Continue with grouping, creation,
and propagation as successive milestones.
