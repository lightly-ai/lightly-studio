# Frame Tag Rows on the Sequence Timeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Show frame tags" checkbox to the 3D workspace timeline. When it is on, the timeline shows one row per frame tag, with bars over the ticks that carry the tag.

**Architecture:** A new read endpoint, `GET …/mcap-sequences/{sequence_id}/tick-tags`, returns the sequence's frame tags grouped by tag. The frontend fetches it only while the checkbox is on. `TagTimelineRows` draws the rows between the timeline toolbar and the object track rows. A tag change in the side panel invalidates the query.

**Tech Stack:** FastAPI + SQLModel (backend), SvelteKit 5 + TanStack Query + hey-api client (frontend), pytest, vitest.

**Spec:** `.experimental/superpowers/specs/2026-11-19-ent-569-timeline-frame-tag-rows-design.md`

## Global Constraints

- Do not add fields to `TickView` or `TickListView`. The tick list must stay unchanged.
- UI copy:
  - checkbox label: `Show frame tags`
  - bar title: `<tag> · Frame N`, or `<tag> · Frames A–B` (1-based, en dash)
- Tags are ordered by name, and `seq_numbers` ascending. Only tags used on at least one tick are returned.
- Load skills before editing:
  - `python-guide`, `backend-guide` and `clean-code` for backend files
  - `frontend-guide` and `clean-code` for frontend files
  - `changelog` for `CHANGELOG.md`

## Review Focus

- **The same tag on non-adjacent ticks.** It must become separate bars. Covered by a test in Task 3.
- **Sparse seq numbers (gaps in `seq_number`).** Adjacency follows tick order, as in `buildTrackRuns`. Covered by a test in Task 3.
- **A tag on a sample that is not a tick of this sequence.** For example, the sequence sample itself, or a tick of another sequence. It must not appear. Covered by a test in Task 1.
- **Toggling on a sequence with no tick tags.** It must render no rows and no error. Covered by a test in Task 3.
- **Switching sequences while the checkbox is on.** The query is keyed by sequence, so the rows update. The checkbox keeps its state. Covered by the query key (Task 4).

---

### Task 1: Resolver for the tag links of a sequence

**Files:**
- Create: `lightly_studio/src/lightly_studio/resolvers/sequence_resolver/get_tag_links.py`
- Modify: `lightly_studio/src/lightly_studio/resolvers/sequence_resolver/__init__.py` (export)
- Test: `lightly_studio/tests/resolvers/sequence_resolver/test_get_tag_links.py`

**Interfaces:**
- Produces: `sequence_resolver.get_tag_links(session: Session, sequence_sample_id: UUID) -> list[tuple[TagTable, int]]`. These are `(tag, seq_number)` pairs for every tag on a tick sample of the sequence, ordered by `TagTable.name`, then `seq_number`.

- [ ] **Step 1: Write the failing tests.** Use `helpers.create_sequence_and_samples` and `sequence_resolver.add_samples`. Tags come from `tag_resolver.create` + `tag_resolver.add_tag_to_sample`.
  - `test_get_tag_links`: tag `b` on ticks 2 and 0, tag `a` on tick 1 → `[("a",1),("b",0),("b",2)]` (compare `(tag.name, seq)`).
  - `test_get_tag_links__no_tags` → `[]`.
  - `test_get_tag_links__ignores_other_sequences`: a tag on a tick of a second sequence, and a tag on the sequence sample itself, are not returned.
- [ ] **Step 2:** Run `uv run pytest tests/resolvers/sequence_resolver/test_get_tag_links.py`. Expected: FAIL (import error).
- [ ] **Step 3: Implement.** Use one `select(TagTable, SampleSequenceLinkTable.seq_number)` joining `SampleTagLinkTable.sample_id == SampleSequenceLinkTable.sample_id` and `TagTable.tag_id == SampleTagLinkTable.tag_id`, where `sequence_sample_id` matches, with `order_by(TagTable.name, seq_number)`.
- [ ] **Step 4:** Rerun. Expected: PASS.

### Task 2: Service, views and route

**Files:**
- Modify: `lightly_studio/src/lightly_studio/models/mcap_sequence_ticks.py` (add views)
- Create: `lightly_studio/src/lightly_studio/services/recording_service/get_tick_tags.py`
- Modify: `lightly_studio/src/lightly_studio/services/recording_service/__init__.py` (export)
- Create: `lightly_studio/src/lightly_studio/api/routes/mcap_sequences/get_tick_tags.py`
- Modify: `lightly_studio/src/lightly_studio/api/routes/mcap_sequences/__init__.py` (include router)
- Test: `lightly_studio/tests/api/routes/mcap_sequences/test_get_tick_tags.py`

**Interfaces:**
- Consumes: `sequence_resolver.get_tag_links` (Task 1); `recording_service.get_ticks` for the dataset membership check (the same pattern as `get_sequence_tracks`).
- Produces:
  - `TickTagView(BaseModel)`: `tag_id: UUID`, `name: str`, `seq_numbers: list[int]` (each field with a `Field(description=…)`)
  - `TickTagListView(BaseModel)`: `tags: list[TickTagView]`
  - `recording_service.get_tick_tags(session, dataset_id, sequence_id) -> TickTagListView | None`
  - Route `GET /datasets/{dataset_id}/mcap-sequences/{sequence_id}/tick-tags`, with operation function `get_tick_tags`, `response_model=TickTagListView`. It returns 404 via `NotFoundError` when the service returns `None`.

- [ ] **Step 1: Write the failing route tests.** Mirror `test_get_ticks.py` (`helpers.create_mcap_sequence`, plus ticks linked with `SampleSequenceLinkTable`; tag the tick samples).
  - `test_get_tick_tags`: tag `occluded` on ticks 0 and 1 → `{"tags":[{"tag_id":…, "name":"occluded","seq_numbers":[0,1]}]}`.
  - `test_get_tick_tags__no_tags` → `{"tags": []}`.
  - `test_get_tick_tags__unknown_sequence` and `test_get_tick_tags__wrong_dataset` → 404.
- [ ] **Step 2:** Run the test. Expected: FAIL (404 on every request).
- [ ] **Step 3: Implement the views, service and route.** The service groups the resolver's ordered pairs by `tag_id`, keeping the order in which each tag is first seen.
- [ ] **Step 4:** Run the test plus `test_get_ticks.py`. Expected: PASS. Then run `make static-checks` in `lightly_studio`. Expected: clean.
- [ ] **Step 5:** Add an `Added` entry to `CHANGELOG.md` (follow the `changelog` skill): "The 3D labeling timeline can show frame tags as rows."

### Task 3: Frontend client, run grouping and tag rows

**Files:**
- Regenerate: `lightly_studio_view/src/lib/api/lightly_studio_local/*` (run `make export-schema` in `lightly_studio`, then `npm run generate-api-client` in `lightly_studio_view`)
- Create: `lightly_studio_view/src/lib/components/PointCloudLabelingWorkspace/FrameTimeline/TagTimelineRows/buildTagRuns.ts` (+ `buildTagRuns.test.ts`)
- Create: `…/FrameTimeline/TagTimelineRows/TagTimelineRows.svelte` (+ `TagTimelineRows.test.ts`)
- Modify: `…/FrameTimeline/TrackTimelineRows/TrackTimelineToolbar/TrackTimelineToolbar.svelte`
- Modify: `…/FrameTimeline/TrackTimelineRows/TrackTimelineRows.svelte`

**Interfaces:**
- Consumes: the generated `TickTagView` type.
- Produces:
  - `buildTagRuns(ticks: readonly TickView[], seqNumbers: readonly number[]): { startIndex: number; endIndex: number }[]`. These are inclusive tick-index runs. Adjacency follows tick order, and unknown seq numbers are ignored.
  - `TagTimelineRows` props: `{ ticks: TickView[]; tags: TickTagView[]; onSelectTick: (seqNumber: number) => void }`. Each tag gets a row with its name label, and each run is a `<button>`:
    - titled as in Global Constraints
    - `onclick` → `onSelectTick(ticks[run.startIndex].seq_number)`
    - neutral fill `bg-muted-foreground/60`
    - placed inside a `TimelineLane` like `TrackTimelineRow`
  - `TrackTimelineToolbar` gets new props `frameTags?: { checked: boolean; onCheckedChange: (checked: boolean) => void }`. When set, it renders a `Checkbox` (`$lib/components/ui/checkbox`) labeled `Show frame tags`.
  - `TrackTimelineRows` gets new props `showFrameTags?: boolean`, `onShowFrameTagsChange?: (checked: boolean) => void` and `frameTags?: TickTagView[]`:
    - It renders `TagTimelineRows` between the toolbar and `object-track-list` when `showFrameTags`.
    - The outer `{#if}` also renders when `onShowFrameTagsChange` is set, so the checkbox is reachable without tracks.
    - The track legend and visibility select still appear only with tracks.

- [ ] **Step 1: Write the failing tests.**
  - `buildTagRuns`, with ticks `[0,1,2,5,6,7]`:
    - `[0,1,6,7]` → `[{0,1},{4,5}]`
    - `[2,5]` → `[{2,3}]` (sparse seq numbers stay adjacent)
    - `[9]` → `[]`
    - `[]` → `[]`
  - `TagTimelineRows`:
    - tags `occluded:[0,1,3]`, `night:[2]` → row labels in input order
    - bar titles `occluded · Frames 1–2`, `occluded · Frame 4`, `night · Frame 3`
    - clicking `occluded · Frame 4` calls `onSelectTick(3)`
    - `tags: []` → renders nothing
  - `TrackTimelineRows`:
    - with `onShowFrameTagsChange` and no tracks, the `Show frame tags` checkbox is shown, and clicking it calls the callback with `true`
    - with `showFrameTags` and `frameTags`, the tag row titles render
- [ ] **Step 2:** Run `npx vitest run src/lib/components/PointCloudLabelingWorkspace/FrameTimeline`. Expected: the new tests FAIL.
- [ ] **Step 3:** Regenerate the client and implement the files above.
- [ ] **Step 4:** Rerun. Expected: PASS.

### Task 4: Wire the query, checkbox state and invalidation

**Files:**
- Create: `…/FrameTimeline/useSequenceTickTags.svelte.ts`
- Create: `…/FrameTimeline/tickTagsQueryKey.ts`
- Modify: `…/FrameTimeline/FrameTimeline.svelte` and `…/FrameTimeline/TimelineContent/TimelineContent.svelte` (pass `showFrameTags`, `onShowFrameTagsChange` and `frameTags` through to `TrackTimelineRows`)
- Modify: `…/PointCloudWorkspaceMainColumn.svelte`
- Modify: `…/WorkspacePanels/WorkspacePanels.svelte`
- Test: `…/FrameTimeline/FrameTimeline.test.ts` (extend)

**Interfaces:**
- Consumes: the generated `getTickTagsOptions` (Task 3).
- Produces:
  - `useSequenceTickTags(getParams: () => { datasetId: string; sequenceId: string; enabled: boolean }) => { query }`. It works like `useSequenceTracks`, with `enabled` gating the request.
  - `TICK_TAGS_QUERY_KEY = [{ _id: 'getTickTags' }]`, which matches every tick-tag query.
- Wiring:
  - `MainColumn` keeps `let showFrameTags = $state(false)`, which survives sequence switches within the workspace. It passes `frameTags={tickTagsQuery.query.data?.tags ?? []}`.
  - In `WorkspacePanels`, `onTagsChange` also calls `queryClient.invalidateQueries({ queryKey: TICK_TAGS_QUERY_KEY })`.

- [ ] **Step 1: Write the failing test.** In `FrameTimeline.test.ts`, render with `showFrameTags: true` and `frameTags: [{tag_id:'t', name:'occluded', seq_numbers:[0]}]`, then assert that the title `occluded · Frame 1` exists.
- [ ] **Step 2:** Run it. Expected: FAIL.
- [ ] **Step 3:** Implement the wiring.
- [ ] **Step 4:** Run `make static-checks` and `make test` in `lightly_studio_view`. Expected: clean, all tests pass.
