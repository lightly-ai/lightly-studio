# Feature: Categorical Metadata Distribution and Filter

**Status:** Implemented; QA ready

**Linear:** [LIG-9585](https://linear.app/lightly/issue/LIG-9585/frontend-categorical-metadata-bar-chart-filter-ui-8-sp)

**Depends on:** [LIG-9584](https://linear.app/lightly/issue/LIG-9584/backend-categorical-metadata-value-counts-endpoint-5-sp)

## Problem and Target User

ML engineers can inspect numeric metadata distributions, but categorical fields such as `city`,
`camera_id`, or a boolean flag are absent from the distribution panel and cannot be filtered there.
They need to spot imbalance and missing metadata, then narrow the grid without leaving the plot.

## Proposed User Flow

1. Open the existing dataset distribution panel and select **Metadata**.
2. Use the existing **Metadata key** selector to choose a numeric or categorical field.
3. Numeric fields continue to show the current histogram. Categorical fields show a horizontal bar
   chart and a compact searchable value selector.
4. Select one or more concrete values or **Missing**. The grid and all distributions update using
   the shared active filter; alternatives for the edited field remain visible through faceting.
5. Deselect every value (or use **Clear**) to remove that field's categorical filter.

## Wireframes

### Loaded categorical field

```text
+--------------------------------------------------+
| Distribution                                  [x]|
| Distribution  [ Metadata                 v ]     |
| Metadata key  [ city                     v ]     |
|                                                  |
| Values        [ 2 selected · Search values  v ]  |
|                                                  |
| Zurich    |████████████████████| 120             |
| Berlin    |██████████          |  64             |
| Missing   |██                  |   8             |
| Other     |█                   |   4  (display)   |
+--------------------------------------------------+

Values popover
+--------------------------------------+
| Search values…                       |
| [x] Zurich                       120 |
| [x] Berlin                        64 |
| [ ] Missing                        8 |
|     Other is an aggregate and cannot |
|     be selected                        |
| [Clear]                              |
+--------------------------------------+
```

The bars for selected concrete values and Missing have a non-colour-only selected treatment.
Clicking a selectable bar toggles the same selection as its checkbox. Other is not interactive.

### Loading, empty, and error

```text
Loading/refetch                 No categorical fields
+---------------------------+  +---------------------------+
| Values [Loading…]         |  | No categorical metadata   |
| Previous bars stay visible|  | is available.             |
+---------------------------+  +---------------------------+

Selected field has no matches  Request failed
+---------------------------+  +---------------------------+
| No matching samples for   |  | Could not load metadata   |
| this metadata field.      |  | distribution. [Retry]     |
+---------------------------+  +---------------------------+
```

## Content and Interaction

- String and boolean fields use categorical bars; integer and float fields keep using histograms.
- Concrete values are ordered by the endpoint (frequency with deterministic ties). **Missing** and
  non-zero **Other** are appended as semantic buckets.
- Values retain typed identity (`string`, `boolean`, or `null`) independently from display labels.
  Literal strings `"Missing"` and `"Other"` therefore remain ordinary selectable values.
- **Missing** means absent key, JSON null, or no metadata row and is represented internally by
  `null`. **Other** is display-only because its members are not returned by the endpoint.
- Multiple values for one key use OR semantics. Filters for different keys and all other active
  filters use AND semantics.
- Selected values remain available in the selector while refetching. A field's own categorical
  filter is excluded only from that field's count query, matching the numeric faceting behavior.
- Empty selection means no categorical filter for the field. The UI never sends an empty `in`
  predicate.
- The selector summary reads **All values**, the selected value for one item, or **N selected**.
- Categorical fields expose the existing distribution settings and expanded-chart actions. Settings
  support top-N, manual value selection, and count/value sorting; they are stored per metadata key.
  The categorical chart remains horizontal and omits **Count by** because the endpoint counts
  samples. Missing and Other remain visible in top-N mode; manual mode is explicitly user-selected.
- For five or fewer concrete values, show direct checkboxes without search. Longer lists add search
  inside the same compact popover; search only narrows returned options and never changes the grid.
- Retain selected values when they are absent from the latest top-20 response so users can still
  deselect them, and summarize active categorical fields in the existing metadata-filter chip area.

## States

- **Loading:** Disable selection until initial data arrives. During later refetches, retain previous
  bars and selections and show a subtle busy indicator.
- **Empty:** If no categorical fields exist, omit categorical groups. If a known selected field has
  no matches, show the field-level empty message rather than an empty chart.
- **Error:** Keep the panel and selectors usable, show a concise error with Retry, and do not clear
  active selections.
- **Success:** Show the chart and value selector. Omit zero-count Missing and Other bars.

## Responsive and Accessibility Requirements

- Keep controls full-width and stacked in the side panel; the value popover must not exceed the
  viewport and its list scrolls independently.
- Every selectable value is keyboard reachable and toggleable with Enter or Space. Escape closes
  the popover and returns focus to its trigger.
- Expose checkbox state, counts, chart labels, selected state, loading state, and disabled Other
  semantics to assistive technology. Do not communicate selection through colour alone.
- Long field/value labels truncate visually but remain available through accessible names/tooltips.
- Touch targets are at least 32 px in the desktop side panel and 44 px in narrow/touch layouts.

## Decision Rationale

- **Reuse the existing source and field selectors:** numeric and categorical metadata are two
  renderings of the same concept, so adding another navigation layer would be needless ceremony.
- **Horizontal bars:** categorical labels remain readable and the existing `BarChart` can be reused.
- **Compact searchable multi-select:** checkboxes are fast for common low-cardinality fields while
  search keeps the top-20 list manageable.
- **Explicit Missing; display-only Other:** Missing maps to a precise predicate; Other does not.
- **Live faceted counts:** the chart continues to explain the current grid without hiding alternative
  values for the field being edited.
- **Follow FiftyOne's useful behavior, not its layout:** FiftyOne supports categorical histograms,
  current-view updates, low-cardinality checkboxes, and search for longer value lists. Lightly keeps
  those interaction principles inside its existing distribution panel rather than adding a second
  full filter sidebar.

## Acceptance Criteria

- [ ] The Metadata source lists numeric, string, and boolean fields in the existing field selector.
- [ ] Numeric fields still render the existing histogram and range filter behavior.
- [ ] Categorical fields render endpoint-ordered horizontal bars with counts.
- [ ] Categorical fields provide a horizontal expanded view and value-specific configuration for
      top-N, manual selection, and count/value sorting without exposing Count by or orientation.
- [ ] Concrete string/boolean values and Missing can be selected by checkbox and bar click.
- [ ] Multiple values for one field filter with OR; filters across fields remain AND.
- [ ] Literal `"Missing"`/`"Other"` values do not collide with semantic buckets.
- [ ] Other is visible when non-zero, clearly non-selectable, and never produces a filter.
- [ ] Grid requests, query keys, filter hashes, counts, and distribution requests use the same
      categorical selection state and update when it changes.
- [ ] A categorical field's own predicate is excluded from its returned counts.
- [ ] Empty selection removes that field's predicate; selections reset on collection change.
- [ ] Active categorical filters appear in metadata-filter chips and stale selected values remain
      removable when absent from the latest response.
- [ ] Loading/refetch, empty, and error states preserve active filters and provide clear feedback.
- [ ] Keyboard, focus, screen-reader, and responsive requirements are covered by tests or manual QA.

## Architecture Contract

### Backend filter extension

- Extend `MetadataOperator` with `in`.
- A categorical field is encoded as one predicate, for example:

```json
{ "key": "city", "op": "in", "value": ["Zurich", "Berlin", null] }
```

- Array members are OR-ed. `null` matches absent keys, explicit JSON null, and samples without a
  metadata row. Different filter objects retain existing AND semantics.
- Concrete members must be homogeneous strings or homogeneous booleans; an optional null may be
  mixed in. Reject empty arrays and unsupported/mixed values with HTTP 422.
- Use literal top-level JSON-key extraction and an outer metadata join whenever null is requested.
  Existing comparison operators and nested-field behavior remain unchanged.
- The value-count response is unchanged; its resolver already removes all own-key predicates.

### Frontend ownership and data flow

- Shared metadata filter storage owns `Record<string, (string | boolean | null)[]>` categorical
  selections and resets it when the collection changes.
- Filter creation combines numeric range predicates with one non-empty categorical `in` predicate
  per key. The combined predicates drive grid requests and every distribution/count request, and
  categorical state is included in query keys/filter hashes.
- `useCategoricalMetadataDistribution.ts` parallels the numeric hook, calls
  `POST /metadata/value-counts`, forwards the reactive `ImageFilter`, maps semantic buckets without
  label-based identity, and keeps prior data during refetch.
- Metadata source groups use a discriminated categorical payload, mutually exclusive with `data`
  and `histogram`. The panel emits `(groupId, typedValue)` when a concrete/Missing bucket toggles.
- `MetadataCategoricalFilter.svelte` owns only the value popover and categorical presentation; the
  shared store remains the source of truth.

### Verification surfaces

- Backend validation/query tests: string/boolean OR, null-only, concrete plus null, AND across keys,
  dotted/apostrophe keys, no metadata row, empty/mixed-array rejection, DuckDB and PostgreSQL paths.
- Frontend unit/component tests: response mapping, request forwarding, filter construction/reset,
  request/query-key propagation, bar/checkbox toggling, Missing versus literal `"Missing"`, disabled
  Other, loading/empty/error, and selected styling.
- Regenerate OpenAPI and the frontend client, then run backend and frontend static checks plus focused
  test suites.

## Non-goals

- Selecting or expanding the aggregated Other bucket.
- Returning/searching the full high-cardinality tail or adding server-side value search.
- Moving categorical filters into the existing left filter panel or adding a new permanent sidebar.
- Changing numeric histogram behavior, class distribution configuration, or count modes.
- Persisting distributions or adding a database migration.

## Assumptions and Open Questions

- Boolean metadata follows the categorical path.
- The endpoint's fixed top 20 is sufficient for this first UI; selected top values remain present
  because own-field filters are excluded.
- The small `in` extension is part of LIG-9585 because Missing and multi-select cannot meet the
  ticket's acceptance criteria with scalar comparison operators.
- Open question for later work: if users need values hidden in Other, add a dedicated value-search
  endpoint rather than pretending an aggregate bucket identifies its members.
