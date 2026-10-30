# Object track keyframes (LIG-11157)

## Goal

Let a person annotate one tracked 3D object at a few ticks while LightlyStudio supplies the required cuboid annotation on every tick where that object is present. Keep authored corrections, generated annotations, and absent intervals clear in the workspace.

## Interaction contract

1. Creating a cuboid can start a track at the active tick. That cuboid is an authored keyframe.
2. Selecting a later tick and adjusting the same track creates another authored keyframe. The interval between the two can use **Interpolate geometry** or **Hold position**.
3. The timeline gives each track a row with visible spans, authored keyframe marks, and a distinct generated segment. Selecting a mark seeks to its tick. Previous/next keyframe controls help review long sequences.
4. Editing a generated cuboid promotes that tick to an authored keyframe and regenerates only the adjacent intervals. A person can mark a tick range **Not present**; no cuboids are generated in a gap, and the same track may resume later.
5. Keep track identity and annotation class stable throughout the track. An annotation is attached to a tick, not to an individual sensor channel.

## Data and calculation rules

- A track is scoped to one sequence for editing even though the current `object_track` table belongs to a dataset. A track cannot span unrelated sequences.
- Use ordered tick positions to identify interval endpoints, including when `seq_number` values are sparse. Interpolation fractions should use anchor timestamps when both endpoints and the target have valid, increasing timestamps; otherwise use tick positions. Define this in one backend/frontend shared contract before persistence is wired.
- Interpolate cuboid centre and full size linearly. Use shortest-path quaternion spherical interpolation for rotation. Interpolate only when both anchors use the same coordinate frame; otherwise require an explicit transform or a new interval boundary.
- For a hold interval, copy the anchor geometry. A frame's `frame_id` belongs to its target tick even when geometry is copied or interpolated.
- Persist or serve a per-tick annotation only inside visible intervals. Mark generated cuboids with `interpolated=true`; authored cuboids remain false. Do not extrapolate outside explicitly chosen bounds or across a gap.
- Preserve authored annotations and existing imported tracks. A track-edit operation must be idempotent, atomic for its affected interval, and must not silently overwrite an imported per-tick annotation. Decide whether existing imported tracks are read-only until explicitly converted.
- The frontend domain currently has `keyframeId`, but the API/database do not persist one. Decide whether `interpolated=false` plus track/tick identity is sufficient or whether an explicit keyframe record is needed before implementing editing and regeneration.

## Small, reviewable increments

### 1. Geometry foundation — started in this contribution

Add a pure interpolation helper and focused tests for centre, size, quaternion rotation, invalid fractions, and incompatible coordinate frames. It accepts a fraction and does not create annotations or write data. This keeps interpolation math reviewable independently from timeline and persistence work.

### 2. Read-only track timeline

Provide sequence-scoped track summaries with ordered tick membership and authored/generated status. Render track rows under the existing tick ruler. Selecting a track or keyframe seeks to the relevant tick; the existing slider still works. Add a component story and a test for sparse tick numbers, gaps, and many tracks.

### 3. Track-aware creation and interval generation

Add an atomic backend operation to create a track with its first authored cuboid, then add/update an endpoint and generate its interval. Include a mode (`hold` or `interpolate`) and explicit bounds. Generate per-tick annotations with the target tick's sample ID and frame ID. Reject conflicting authored/imported annotations, mismatched classes/sources/coordinate frames, and invalid tick ranges. Test rerunning the operation and failure rollback.

### 4. Editing and review UI

Connect create/extend controls to the operation. Show authored and generated states in the timeline and inspector. Correcting a generated cuboid inserts an authored keyframe and regenerates only its neighboring intervals. Support undo or a clear cancel path before a bulk interval change is committed. Test the full interaction across three keyframes.

### 5. Presence gaps and export checks

Add explicit not-present intervals and resume behavior. Verify rendering, per-tick retrieval, and export for a track that disappears and returns. Confirm that generated cuboids are absent in the gap and that other tracks are unaffected.

## First release acceptance

- A person can annotate a moving cuboid using two authored ticks and review generated cuboids between them.
- A correction at an intermediate tick remains authored after reloading and changes only its two neighboring intervals.
- A static interval can hold geometry without repeated per-tick editing.
- A gap has no cuboids; the same track ID may resume after it.
- Existing imported annotations and tracks are not changed by merely opening or browsing the sequence.

## Decisions to settle before increment 3

1. Do we allow editing imported tracks directly, or require an explicit conversion into a managed track?
2. Should interpolation use tick time when available, with ordinal fallback, or always ordinal positions?
3. Does the first release need a visible preview of all affected ticks before committing an interval?
