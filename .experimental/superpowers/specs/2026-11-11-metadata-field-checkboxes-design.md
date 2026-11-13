# Metadata field checkboxes instead of filter chips

## Intent

The old stack behind PR #3168 (`jonas/md-1-range-chips` … `jonas/md-6-remove-picker`) shows a
chip for each active metadata filter. The chip is at the top of the filter panel. The control
that changes the filter (the slider or the value list) is far below it. You see the state in one
place and change it in a different place.

This design removes all metadata filter chips. The state of a filter shows on its field, in the
Metadata section. Active fields move to the top of the section, so the state and the control are
in the same place.

## Goals

- Each field in the Metadata section shows whether it filters the samples.
- You can reset one field, or all fields, from the section.
- Active fields are at the top, separated from the other fields.
- The field you are working on does not move under your mouse, and it keeps focus.

## Non-goals

- No "remember last range" behavior. When you uncheck a field, the filter is gone. Checking it
  again does not restore it. (The base has this behavior in `useMetadataFilterChips`. We drop it.)

## Anti-goals

- A field that jumps to a new position while you drag its slider.
- Losing keyboard focus or scroll position on the field after it moves.
- Two different places that show the same filter state.

## Starting point

- Make a new stack. Do not change the old `md-*` branches. Jonas deletes them later.
- Base: `jonas/fl-6-categorical-values` (the FilterList unification stack).
- You can reuse work from the old stack where it does not depend on chips:
  - `7077f10cc` Make numeric metadata fields collapsible
  - `110b60045` Show categorical metadata fields like numeric ones
  - `d402ffe56` Put all metadata filters in one Metadata section
  - `f84eeddcc` Remove the categorical field picker and unused DimensionFilters
- Do not use the chip commits `4fbae5288`, `dfe605cc8` (`useRangeChips`) or `6ef391727`
  (`useDimensionFilterChips`).
- Workflow: build the whole feature on one branch. Jonas tests it end to end. Then cut it into
  stacked PRs.

## Behavior

Fields in scope: all fields in `CombinedMetadataDimensionsFilters`. These are image width and
height (`useDimensions`), video width, height, fps and duration, video frame number, numeric
metadata, and categorical metadata. All fields act the same.

Categorical fields are listed for **all** collections that show the Metadata section, including
video and video-frame collections (decided by Jonas). Today they are listed only for image
collections (`categoricalFields = isImageCollection ? categoricalKeys : []`), and the chips are
the only place that shows a video categorical filter. For videos, query the value counts with a
video filter (`filter_type: 'video'`), as `useVideoMetadataDistributionSource.svelte.ts` does.

### Video field filters

The video field filters are fields like all others (decided by Jonas):
`VideoFieldBoundsFilters` (width, height, fps, duration) and `VideoFrameBoundsFilter` (frame
number). Each one is its own row with a checkbox, short value, ✕, expand chevron and slider. It
is checked when its range is narrower than its bounds. It reorders like the other fields. In the
order inside a group, the video fields take the place of the image width and height.

Today these components render their sliders in a different way from `MetadataFilterItem`.
Render each video field with the same field row as the other numeric fields (for example
`MetadataFilterItem`), so that all rows look and act the same.

### Field row

Mockup: version A with a per-field ✕ (accepted).

```
▾ Metadata                         [✕ Clear]
[✓] ▾ width            200 – 640          ✕
      ──●━━━━━━━━━━●────
[✓] ▸ split            2 of 3             ✕
────────────────────────────────────────────
[ ] ▸ brightness
[ ] ▸ height
[ ] ▸ source
```

Each row has, from left to right: checkbox, expand chevron, field name, short value (only when
checked), ✕ button (only when checked).

- **Checked** means the field is not at its default:
  - Numeric field or dimension: the applied range is narrower than the bounds.
  - Categorical field: one or more values are selected.
- **Short value:** numeric shows `min – max` with the same formatting and unit as the slider
  labels. Categorical shows `N of M` (selected of all values). *(My call; Jonas did not object.)*
  When the value count is not loaded yet (field collapsed), show `N selected`. *(My call.)*
- **Uncheck the checkbox** or **click ✕**: that field resets to its default. Numeric resets to its
  bounds. Categorical clears its selected values. Both controls do the same thing.
- **Click an unchecked checkbox**: the field expands. No filter is set. The box stays unchecked
  until you set a filter.
- Use the existing ✕ icon button style from `MetadataFieldHeader` (`onRemove`).
- Accessible names: checkbox and ✕ name the field, for example "Clear width filter".

### Order and separator

- Checked fields first, then a plain horizontal line, then the unchecked fields.
- Inside each group, keep today's order (dimensions, numeric, categorical). *(My call.)*
- No line when one of the two groups is empty. *(My call.)*
- Field search (more than `MANY_FIELDS` fields) filters both groups.

### When a field moves

- A field moves to the other group only when its filter is **applied**:
  - Slider: on `onValueCommit`, that is, when you release the mouse (or when the keyboard commit
    fires). Nothing moves while you drag.
  - Categorical: when you click a value, Select all, or Clear.
  - Checkbox, ✕, section Clear: right away.
- Because the group follows the applied filter state, filters set from somewhere else (for
  example the distribution panel) also move the field.

### Focus after a move

- The field that moved keeps its expanded state.
- Keyboard focus stays on the control you used (slider thumb, value checkbox).
- The field scrolls into view in the filter panel if it moved out of view.
- Expected: a keyed `{#each}` over one ordered list keeps the DOM node when it moves, so focus
  stays. Verify this. If it does not hold, restore focus and scroll explicitly.

### Section Clear

- A `FilterActionButton` with label "Clear" and the X icon in the Metadata section header row,
  the same as Clear in the Labels `FilterList`.
- It shows only when one or more fields are checked. *(My call.)*
- It resets all fields in the section: image dimensions, video fields, frame number, numeric
  metadata and categorical metadata.

### Analytics

The deleted `useMetadataFilterChips` sends `metadata_filter_changed` with
`action: 'enabled' | 'disabled'`. Keep the event: the checkbox, the ✕ and the section Clear send
it with `action: 'disabled'` for each field they reset. Setting a filter keeps the events it sends
today. *(My call.)*

### Chips removed

- Remove `MetadataFilterChips` and its hooks (`useMetadataFilterChips` and helpers) from the
  route `+layout.svelte` and from the code base, for numeric and categorical filters.
- Keep `FilterChip`. `ConfusionCellFilterItem` and other code still use it.
- No e2e spec uses the `metadata-filter-chip-*` test IDs. Only the unit tests in
  `MetadataFilterChips/` use them, and those are deleted with the component.

## Constraints

- Follow `.agents/skills/frontend-guide` (Svelte 5 runes, Shadcn, Tailwind, vitest, Storybook).
- User-visible names follow `.agents/skills/glossary`.
- Existing e2e specs for Images, Videos, Annotations and sample details must pass.
- CHANGELOG entry for the user-visible change.

## Left to the builder

- Where the "is checked" and "reset" logic lives (a small helper per field kind is fine).
- How to build one ordered list from the three field kinds.
- The exact checkbox component (Shadcn `Checkbox` is expected).
- Test split between unit tests and component tests.
- How to slice the branch into PRs (follow `.agents/skills/pull-requests`).

## Changes after hands-on testing (2026-11-12)

Jonas tested the branch and changed these points. They replace the matching parts above.

- The field name is left-aligned, and the field content is indented under the chevron.
- The short value shows only while the field is collapsed. Categorical fields always use
  "N of M"; the value counts are also requested for collapsed active fields.
- The section Clear is in its own row below the field search, always visible, and disabled
  when no field filters.
- While a field search is active, the list keeps its height, so the search box does not move.
- The field search highlights the matching text in the field names.
- A field that moves stays at the same screen position: the panel scrolls by the distance it
  moved, and the scroll position inside the field is kept.
