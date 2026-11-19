# ENT-569: Frame tag rows on the sequence timeline

## Intent

In the 3D labeling workspace, users want to see **how much of a sequence a frame tag
covers, and where**. A checkbox on the frame timeline shows one row per frame tag, with
bars over the ticks that carry it. This gives an overview of how wide each tag's marking
is. Frame-by-frame inspection is not the goal.

## Goals

- A "Show frame tags" checkbox in the timeline toolbar.
- When it is on, one row per frame tag used in the sequence, labeled with the tag name.
- Consecutive tagged ticks render as one bar, the same way track runs do.
- The rows stay in sync when frame tags change in the right side panel.

## Non-goals

- Editing tags from the timeline (tagging ranges, dragging bars).
- Sequence tags. These are tags on the sequence sample, not on its ticks.
- Filtering or coloring by tag.

## Anti-goals

- Slowing down playback or buffering. The tick list that drives them must not grow.

## Approaches

1. **New endpoint for tick tags (chosen).** Returns tags grouped by tag, and is fetched
   only while the checkbox is on. The tick list stays lean, and the shape matches the rows.
2. Add `tags` to every `TickView`. Every tick carries tags whether or not anyone needs
   them, and a tag edit refetches the list that drives playback. Rejected.
3. Frontend-only, using the tick detail of every tick. One request per tick. Rejected.

Kondrat picked 1, with option B in the UI (one row per tag).

## Design

### Backend

- `GET /datasets/{dataset_id}/mcap-sequences/{sequence_id}/tick-tags` →
  `TickTagListView { tags: list[TickTagView] }`, where
  `TickTagView { tag_id: UUID, name: str, seq_numbers: list[int] }`.
  - The query joins the sequence's sample links (`SampleSequenceLinkTable`) with
    `SampleTagLinkTable` and `TagTable`. Only tags on at least one tick are returned.
  - `seq_numbers` is ascending. Tags are ordered by name.
  - Unknown sequence, or a sequence outside the dataset → 404. This is the same
    membership check as `get_ticks`.
- Layout follows the existing ticks code:
  - the route lives in `api/routes/mcap_sequences/get_tick_tags.py`
  - the service lives in `services/recording_service/`
  - the query lives in a resolver
  - the views live in `models/mcap_sequence_ticks.py`
- Then regenerate the frontend API client.

### Frontend

- `TrackTimelineToolbar`: a "Show frame tags" checkbox, off by default (*my call*).
- A query hook `useSequenceTickTags`, enabled only while the checkbox is on, keyed by
  sequence. The workspace invalidates it next to the existing `tickDetails.refetch()`
  when frame tags change.
- `TagTimelineRows` renders under the ruler and above the object track rows. It uses
  one `TagTimelineRow` per tag: the label on the left, with layout and run bars styled
  like `TrackTimelineRow`.
- Generalize the run building in `buildTrackRuns` so tag rows reuse it: group sorted
  tick indices into consecutive runs (*my call*).
- Clicking a bar seeks to its first tick (*my call*).
- Bars use one neutral color, distinct from the track colors (*my call*).

## Left to the builder

- Exact styling, and how the tag rows share vertical space with the track rows' resizer.
- Whether the checkbox state persists across sequences. Default: it lives in workspace
  state for the session.

## Testing

- Backend: resolver and route tests:
  - a tag on non-contiguous ticks
  - two tags
  - no tags → empty list
  - wrong dataset → 404
- Frontend: unit test for the run grouping; component test for the toggle and the rows.
