# Metadata Field Checkboxes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace all metadata filter chips with a checkbox, short value and ✕ on each field of
the Metadata section, with active fields ordered first.

**Architecture:** A pure module (`metadataFields.ts`) describes every field (image dimension,
video field, frame number, numeric metadata, categorical metadata) as one `MetadataField` type
and orders them. A hook (`useMetadataFieldList`) reads the existing stores, builds the field list,
and owns commit and reset. `CombinedMetadataDimensionsFilters` renders one keyed list from it, with
a separator and a section Clear, and keeps focus on a field that moves.

**Tech Stack:** SvelteKit, Svelte 5 runes, TypeScript, Shadcn (`Checkbox`), Tailwind, TanStack
Query, vitest + @testing-library/svelte (jsdom), Playwright.

**Spec:** `.experimental/superpowers/specs/2026-11-11-metadata-field-checkboxes-design.md`

All paths below are relative to `lightly_studio_view/` unless they start with `CHANGELOG.md`.
`CMDF` = `src/lib/components/CombinedMetadataDimensionsFilters`.

## Global Constraints

- Load `.agents/skills/frontend-guide/SKILL.md` before editing frontend files; load
  `.agents/skills/best-practices/SKILL.md` for new modules; `.agents/skills/glossary/SKILL.md` for
  user-visible text; `.agents/skills/changelog/SKILL.md` for `CHANGELOG.md`.
- New branch from `jonas/fl-6-categorical-values`. Do not change the `jonas/md-*` branches.
- No chips for metadata filters anywhere. Keep `FilterChip` (used by `ConfusionCellFilterItem`).
- No "remember last range": unchecking resets; checking again restores nothing.
- A field changes group only when its filter is applied (slider `onValueCommit`, categorical
  click). Nothing moves while you drag.
- Analytics: each reset from the checkbox, ✕ or section Clear sends
  `metadata_filter_changed` with `{ collection_id, field_name, action: 'disabled' }`.
- Validation per task: `cd lightly_studio_view && make static-checks` and the named vitest files
  (`npx vitest run <files>`).

## Review Focus

1. A numeric metadata key named `width` or `height` next to the image dimensions: both rows must
   show and act on their own store. → Task 2 test `ids differ for a metadata key named width`.
2. A field whose bounds are equal (`min === max`), for example a constant metadata value: it is
   never checked. → Task 2 test `a field with equal bounds is never active`.
3. A filter set from somewhere else (distribution panel writes the store): the field becomes
   checked and moves. → Task 4 test `a store change from outside makes the field active`.
4. The global "Clear all filters" resets the stores: no row checked, no separator, no section
   Clear. → Task 6 test `hides the separator and Clear when no field is active`.
5. Field search while fields are active: ordering applies to the search result, and the line shows
   only when both groups have rows. → Task 6 test `search result keeps the active-first order`.

---

### Task 1: New branch, reuse the old non-chip commits, remove the chips

**Files:**
- Delete: `src/lib/components/MetadataFilterChips/` (whole folder)
- Modify: `src/lib/components/index.ts` (drop the `MetadataFilterChips` export if present)
- Modify: `CMDF/CombinedMetadataDimensionsFilters.svelte` (drop the `MetadataFilterChips` usage)
- Modify: `src/routes/datasets/[dataset_id]/[collection_type]/[collection_id]/+layout.svelte`

**Interfaces:**
- Produces: the branch `jonas/mf-0-checkboxes` with `MetadataFieldHeader`, collapsible fields,
  one Metadata section, and no chip code.

- [ ] **Step 1: Create the branch**

```bash
git switch -c jonas/mf-0-checkboxes jonas/fl-6-categorical-values
```

- [ ] **Step 2: Cherry-pick the reusable commits in order**

```bash
git cherry-pick 7077f10cc 110b60045 d402ffe56 f84eeddcc
```

`7077f10cc` and `110b60045` apply cleanly. `d402ffe56` conflicts in `MetadataFilterChips/*`
because the chip commits are not on this branch. Resolve by `git rm -r` of
`src/lib/components/MetadataFilterChips`, and in `CombinedMetadataDimensionsFilters.svelte` take
the `d402ffe56` version and delete the `MetadataFilterChips` import and the
`<MetadataFilterChips … />` line. Remove the `CHANGELOG.md` line that `d402ffe56` adds (Task 8
writes the entry). `git cherry-pick --continue`, then the last commit.

- [ ] **Step 3: Remove leftover chip references**

`grep -rn "MetadataFilterChips\|useMetadataFilterChips" src` must print nothing. Remove any
hit (barrel export, layout import).

- [ ] **Step 4: Verify**

Run: `make static-checks && npx vitest run src/lib/components/CombinedMetadataDimensionsFilters src/lib/components/MetadataFieldHeader src/lib/components/MetadataCategoricalFilter`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "Remove the metadata filter chips"
```

---

### Task 2: Field model and ordering

**Files:**
- Create: `CMDF/metadataFields.ts`
- Test: `CMDF/metadataFields.test.ts`

**Interfaces:**
- Produces:

```ts
export type Range = { min: number; max: number };
export type RangeSource = 'dimension' | 'video' | 'frame' | 'numeric';
export interface RangeField {
    kind: 'range'; id: string; source: RangeSource; key: string;
    title: string; unit: string; bound: Range; value: Range;
}
export interface CategoricalField {
    kind: 'categorical'; id: string; source: 'categorical'; key: string;
    title: string; selected: CategoricalMetadataValue[];
}
export type MetadataField = RangeField | CategoricalField;
export const fieldId = (source: RangeSource | 'categorical', key: string): string; // `${source}:${key}`
export const isFieldActive = (field: MetadataField): boolean;
export const orderByActive = (fields: MetadataField[]): { fields: MetadataField[]; activeCount: number };
export const formatRangeSummary = (field: RangeField): string;
```

- [ ] **Step 1: Write the failing tests**

```ts
const range = (over: Partial<RangeField> = {}): RangeField => ({
    kind: 'range', id: fieldId('numeric', 'score'), source: 'numeric', key: 'score',
    title: 'score', unit: '', bound: { min: 0, max: 1 }, value: { min: 0, max: 1 }, ...over
});
const categorical = (selected: CategoricalMetadataValue[]): CategoricalField => ({
    kind: 'categorical', id: fieldId('categorical', 'split'), source: 'categorical',
    key: 'split', title: 'split', selected
});

it('a range at its bounds is not active', () => expect(isFieldActive(range())).toBe(false));
it('a narrowed range is active', () =>
    expect(isFieldActive(range({ value: { min: 0.2, max: 1 } }))).toBe(true));
it('a field with equal bounds is never active', () =>
    expect(isFieldActive(range({ bound: { min: 5, max: 5 }, value: { min: 5, max: 5 } }))).toBe(false));
it('a categorical field with selected values is active', () => {
    expect(isFieldActive(categorical([]))).toBe(false);
    expect(isFieldActive(categorical([null]))).toBe(true);
});
it('orders active fields first and keeps the order inside each group', () => {
    const a = range({ id: 'numeric:a', key: 'a' });
    const b = range({ id: 'numeric:b', key: 'b', value: { min: 0.5, max: 1 } });
    const c = categorical(['train']);
    expect(orderByActive([a, b, c])).toEqual({ fields: [b, c, a], activeCount: 2 });
});
it('ids differ for a metadata key named width', () =>
    expect(fieldId('dimension', 'width')).not.toBe(fieldId('numeric', 'width')));
it('formats integer ranges with the unit', () =>
    expect(formatRangeSummary(range({ unit: 'px', bound: { min: 0, max: 1024 }, value: { min: 200, max: 640 } })))
        .toBe('200px – 640px'));
it('formats float ranges like the slider labels', () =>
    expect(formatRangeSummary(range({ value: { min: 0.25, max: 0.5 } })))
        .toBe(`${formatFloat(0.25)} – ${formatFloat(0.5)}`));
```

- [ ] **Step 2: Run to verify they fail**

Run: `npx vitest run CMDF/metadataFields.test.ts` — Expected: FAIL (module not found).

- [ ] **Step 3: Implement `metadataFields.ts`**

Active range: `value.min > bound.min || value.max < bound.max`. Integer check and formatting the
same as `MetadataFilterItem` (`formatInteger` when both bounds are integers, else `formatFloat`).
Separator in the summary is ` – ` (en dash with spaces). `orderByActive` is a stable partition.

- [ ] **Step 4: Run to verify they pass** — same command, Expected: PASS.

- [ ] **Step 5: Commit** — `git commit -m "Add the metadata field model and active-first order"`

---

### Task 3: Checkbox, short value and ✕ in the field header

**Files:**
- Modify: `src/lib/components/MetadataFieldHeader/MetadataFieldHeader.svelte`
- Test: `src/lib/components/MetadataFieldHeader/MetadataFieldHeader.test.ts`

**Interfaces:**
- Produces new optional props on `MetadataFieldHeader`:
  - `checked?: boolean` — when not `undefined`, a Shadcn `Checkbox` shows before the chevron.
  - `summary?: string` — short value, shown only when `checked`.
  - `onClear?: () => void` — ✕ icon button shown only when `checked`; also called on uncheck.
- Existing `status`, `expanded`, `onToggleExpanded`, `onRemove` keep their behavior.

- [ ] **Step 1: Write the failing tests**

```ts
it('shows checkbox, summary and clear button for an active field', () => {
    render(MetadataFieldHeader, { props: { title: 'width', checked: true, summary: '200px – 640px', onClear: vi.fn(), expanded: false, onToggleExpanded: vi.fn() } });
    expect(screen.getByRole('checkbox', { name: 'width filter' })).toBeChecked();
    expect(screen.getByText('200px – 640px')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Clear width filter' })).toBeInTheDocument();
});
it('hides summary and clear button for an inactive field', () => {
    render(MetadataFieldHeader, { props: { title: 'width', checked: false, summary: 'x', onClear: vi.fn() } });
    expect(screen.getByRole('checkbox', { name: 'width filter' })).not.toBeChecked();
    expect(screen.queryByText('x')).toBeNull();
    expect(screen.queryByRole('button', { name: 'Clear width filter' })).toBeNull();
});
it('unchecking calls onClear', async () => {
    const onClear = vi.fn();
    render(MetadataFieldHeader, { props: { title: 'width', checked: true, onClear } });
    await fireEvent.click(screen.getByRole('checkbox', { name: 'width filter' }));
    expect(onClear).toHaveBeenCalledOnce();
});
it('checking a collapsed field expands it and does not clear', async () => {
    const onClear = vi.fn(); const onToggleExpanded = vi.fn();
    render(MetadataFieldHeader, { props: { title: 'width', checked: false, expanded: false, onClear, onToggleExpanded } });
    await fireEvent.click(screen.getByRole('checkbox', { name: 'width filter' }));
    expect(onToggleExpanded).toHaveBeenCalledOnce();
    expect(onClear).not.toHaveBeenCalled();
    expect(screen.getByRole('checkbox', { name: 'width filter' })).not.toBeChecked();
});
it('checking an expanded field does nothing', async () => {
    const onToggleExpanded = vi.fn();
    render(MetadataFieldHeader, { props: { title: 'width', checked: false, expanded: true, onToggleExpanded } });
    await fireEvent.click(screen.getByRole('checkbox', { name: 'width filter' }));
    expect(onToggleExpanded).not.toHaveBeenCalled();
});
```

- [ ] **Step 2: Run to verify they fail** — `npx vitest run src/lib/components/MetadataFieldHeader` — FAIL.

- [ ] **Step 3: Implement**

The checkbox is controlled: pass `checked` and handle `onCheckedChange`; never keep local checked
state (it stays unchecked until a filter is applied). ✕ uses the same `IconButton` markup as
`onRemove`, with `aria-label="Clear {title} filter"`. Summary uses `text-xs text-muted-foreground`
and truncates.

- [ ] **Step 4: Run to verify they pass** — same command, PASS.

- [ ] **Step 5: Commit** — `git commit -m "Add checkbox, short value and clear to the metadata field header"`

---

### Task 4: `useMetadataFieldList` — one list over all filter stores

**Files:**
- Create: `CMDF/useMetadataFieldList.svelte.ts`
- Test: `CMDF/useMetadataFieldList.svelte.test.ts`

**Interfaces:**
- Consumes: Task 2 types; `useDimensions()`, `useVideoBounds(collectionId)`,
  `useVideoFramesBounds(collectionId)`, `useMetadataFilters(collectionId)`, `usePostHog()`.
- Produces:

```ts
export interface UseMetadataFieldListParams {
    getCollectionId: () => string;
    getShowImageDimensions: () => boolean;
    getIsVideos: () => boolean;
    getIsVideoFrames: () => boolean;
    getCategoricalKeys: () => string[];
    /** Called after a range commit, for the existing range analytics. */
    onRangeCommitted?: (key: string, min: number, max: number) => void;
}
export interface UseMetadataFieldListReturn {
    readonly fields: MetadataField[]; // default order
    commitRange: (id: string, range: Range) => void;
    reset: (id: string) => void;
    resetAll: () => void;
}
export function useMetadataFieldList(params: UseMetadataFieldListParams): UseMetadataFieldListReturn;
```

Default order and titles:
1. Image dimensions (when `getShowImageDimensions()`): `dimension:width` "Width" px,
   `dimension:height` "Height" px — store `useDimensions` (`min_width`/`max_width`, …).
2. Video fields (when `getIsVideos()`): `video:width` "Width" px, `video:height` "Height" px,
   `video:fps` "FPS" (omit when its bounds are equal, as today), `video:duration_s` "Duration" s
   — store `useVideoBounds`.
3. Frame number (when `getIsVideoFrames()`): `frame:frame_number` "Frame number" — store
   `useVideoFramesBounds`.
4. Numeric metadata: `numeric:<key>`, title = key, in `metadataBounds` key order, same
   filter as today's `numericalMetadata`.
5. Categorical: `categorical:<key>` for each of `getCategoricalKeys()`, `selected` from
   `categoricalMetadataValues[key] ?? []`.

Pass `getCollectionId()` to the video hooks (today the components read `page.params.collection_id`;
the layout passes the same id for video routes — verify in the layout and keep whichever id the
old components used).

- [ ] **Step 1: Write the failing tests**

Set the global stores directly (as `useMetadataFilters.test.ts` does) and mock `usePostHog`.

```ts
it('lists dimensions, numeric and categorical fields in default order', () => { /* ids equal
  ['dimension:width','dimension:height','numeric:score','categorical:split'] */ });
it('lists video fields and omits fps with equal bounds', () => { /* ids equal
  ['video:width','video:height','video:duration_s', …] */ });
it('commitRange writes only the store of that field', () => {
  /* commitRange('numeric:width', {min:2,max:3}) changes metadataValues.width, not dimensions */ });
it('reset sets a range back to its bounds and tracks disabled', () => {
  /* expect trackEvent('metadata_filter_changed', { collection_id, field_name: 'score', action: 'disabled' }) */ });
it('reset clears categorical values and tracks disabled', () => {});
it('resetAll resets every field and tracks each active one once', () => {});
it('a store change from outside makes the field active', () => {
  /* updateCategoricalMetadataValues({ split: ['train'] }) → fields find split active */ });
```

- [ ] **Step 2: Run to verify they fail** — `npx vitest run CMDF/useMetadataFieldList.svelte.test.ts` — FAIL.

- [ ] **Step 3: Implement**

Read stores with `fromStore`. `commitRange` calls `onRangeCommitted(key, min, max)`; `reset` and
`resetAll` do not call it. `resetAll` tracks only fields that were active. Reset of categorical
deletes the key from `categoricalMetadataValues` (same as the layout's `clearCategoricalValues`).

- [ ] **Step 4: Run to verify they pass** — same command, PASS.

- [ ] **Step 5: Commit** — `git commit -m "Add one field list over all metadata filter stores"`

---

### Task 5: Categorical value counts per field, also for videos

**Files:**
- Create: `src/lib/components/CategoricalMetadataFilters/useCategoricalFieldCounts.svelte.ts`
- Delete: `src/lib/components/CategoricalMetadataFilters/CategoricalMetadataFilters.svelte`
- Modify: `src/lib/hooks/useCategoricalMetadataDistribution/useCategoricalMetadataDistribution.svelte.ts` (export `MetadataValueCountsFilter`)
- Modify: `src/lib/components/MetadataCategoricalFilter/MetadataCategoricalFilter.svelte`, `MetadataCategoricalFilterLayout.svelte`, `MetadataCategoricalFilterList.svelte`
- Test: `src/lib/components/CategoricalMetadataFilters/useCategoricalFieldCounts.svelte.test.ts`, `src/lib/components/MetadataCategoricalFilter/MetadataCategoricalFilter.test.ts`

**Interfaces:**
- Produces:

```ts
export function useCategoricalFieldCounts(getOptions: () => {
    collectionId: string;
    filter?: MetadataValueCountsFilter; // tagged 'image' | 'video'; undefined = no filter
    expandedFields: string[];
}): {
    readonly distributions: Record<string, CategoricalMetadataBucket[]>;
    readonly loading: boolean;
    readonly updating: boolean;
    readonly error: string | undefined;
    refetch: () => void;
};
```

- New props on `MetadataCategoricalFilter` (list layout only), forwarded to `MetadataFieldHeader`:
  `checked?: boolean`, `onClearField?: () => void`. The header `summary` is `"{n} of {m}"` when
  `buckets.length > 0`, else `"{n} selected"`. The header `status` shows only `Updating…`.

- [ ] **Step 1: Write the failing tests**

```ts
// useCategoricalFieldCounts
it('requests only expanded fields with the given filter', () => { /* body.fields = ['split'],
   body.filters = { filter_type: 'video', … } */ });
it('does not request when no field is expanded', () => {});
// MetadataCategoricalFilter (list layout)
it('shows "2 of 3" when values are loaded', () => {});
it('shows "2 selected" when the field is collapsed and values are not loaded', () => {});
it('clicking the clear button calls onClearField', async () => {});
```

- [ ] **Step 2: Run to verify they fail.**

- [ ] **Step 3: Implement** — move the query logic out of `CategoricalMetadataFilters.svelte`
  unchanged except the filter is passed in already tagged (no more `filter_type: 'image'` inside).

- [ ] **Step 4: Run to verify they pass.**

- [ ] **Step 5: Commit** — `git commit -m "Query categorical value counts per field with an image or video filter"`

---

### Task 6: One ordered list in the Metadata section

**Files:**
- Modify: `CMDF/CombinedMetadataDimensionsFilters.svelte`
- Modify: `CMDF/MetadataFilterItem/MetadataFilterItem.svelte`
- Modify: `src/routes/datasets/[dataset_id]/[collection_type]/[collection_id]/+layout.svelte`
- Delete: `src/lib/components/VideoFieldBoundsFilters/`, `src/lib/components/VideoFrameBoundsFilter/` (and their barrel exports, if any)
- Test: `CMDF/CombinedMetadataDimensionsFilters.test.ts` (create)

**Interfaces:**
- Consumes: Tasks 2–5.
- `MetadataFilterItem` new props: `onClear?: () => void`. It computes `checked` and `summary`
  itself with `isFieldActive`/`formatRangeSummary` semantics (pass a `RangeField` or compute from
  `bound`/`value`/`unit` — builder's choice) and forwards them to `MetadataFieldHeader`.
- `CombinedMetadataDimensionsFilters` props change:
  - remove `isImageCollection`, `categoricalFilter`;
  - add `categoricalCountsFilter?: MetadataValueCountsFilter`;
  - keep `collectionId`, `showDimensions`, `isVideos`, `isVideoFrames`, `onFilterChanged`,
    `categoricalKeys`, `onCategoricalValueToggle`, `onCategoricalValuesSet`,
    `onCategoricalValuesClear`.
- Layout passes `categoricalKeys={categoricalMetadataKeys}` for all collections and
  `categoricalCountsFilter`: images → `{ ...$imageFilterFromHook, filter_type: 'image' }`,
  videos → `{ ...$videoFilterFromHook, filter_type: 'video' }`, captions and video frames →
  `undefined`.

Render rules:
- Top row of the section content: the search input (when `fieldCount > MANY_FIELDS`) and, right
  aligned, `<FilterActionButton label="Clear" icon={X} onclick={list.resetAll} />` only when
  `activeCount > 0`. (Not inside the `Segment` trigger: a button inside the collapsible trigger
  would toggle the section.)
- One `{#each ordered.fields as field, index (field.id)}`; before the row at
  `index === ordered.activeCount` when `activeCount > 0`, render
  `<hr data-testid="metadata-active-separator" class="border-border" />`.
- Search filters `list.fields` by title before `orderByActive`.
- Expanded state is keyed by `field.id` (update `isFieldExpanded` callers).
- Each row root has `data-field-id={field.id}` (Task 7 uses it).

- [ ] **Step 1: Write the failing tests** (render with the global stores set, mock the counts query)

```ts
it('renders active fields first with a separator', () => { /* score narrowed → rows order
   ['numeric:score', 'dimension:width', …], separator after the first row */ });
it('hides the separator and Clear when no field is active', () => {});
it('hides the separator when every field is active', () => {});
it('Clear resets all fields', async () => { /* click Clear → stores at bounds, no checked box */ });
it('✕ on a row resets only that field', async () => {});
it('search result keeps the active-first order', async () => {});
it('lists categorical fields for a video collection', () => {});
it('lists video fields with checkboxes and no image dimensions', () => {});
```

- [ ] **Step 2: Run to verify they fail.**

- [ ] **Step 3: Implement** per the render rules.

- [ ] **Step 4: Run to verify they pass**, plus `make static-checks`.

- [ ] **Step 5: Commit** — `git commit -m "Show metadata fields with checkboxes, active fields first"`

---

### Task 7: Keep focus on a field that moves

**Files:**
- Create: `CMDF/keepFocusOnMove.svelte.ts`
- Modify: `CMDF/CombinedMetadataDimensionsFilters.svelte`
- Test: `CMDF/keepFocusOnMove.svelte.test.ts` with a small harness component `CMDF/KeepFocusOnMoveHarness.test.svelte`

**Interfaces:**
- Produces: `export function keepFocusOnMove(getContainer: () => HTMLElement | undefined, getOrder: () => string[]): void`

Approach: in `$effect.pre` that reads `getOrder()`, store `document.activeElement` if it is inside
the container. In `$effect` that reads `getOrder()`, if the stored element is connected and not
focused, call `focus({ preventScroll: true })`; then call `scrollIntoView?.({ block: 'nearest' })`
on its `[data-field-id]` ancestor. Moving a DOM node in a keyed `{#each}` can blur it, so do not
rely on the keyed block alone.

- [ ] **Step 1: Write the failing tests**

```ts
it('keeps focus on an input whose row moves to the top', async () => {
    // harness renders rows ['a','b'] each with a button; focus b's button; set order ['b','a']
    expect(document.activeElement).toBe(screen.getByRole('button', { name: 'b' }));
});
it('scrolls the moved row into view', async () => {
    // Element.prototype.scrollIntoView = vi.fn(); after the move it was called on row b
});
it('does nothing when focus is outside the container', async () => {});
```

- [ ] **Step 2: Run to verify they fail.**
- [ ] **Step 3: Implement and call it in `CombinedMetadataDimensionsFilters` with the ordered ids.**
- [ ] **Step 4: Run to verify they pass.**
- [ ] **Step 5: Commit** — `git commit -m "Keep focus on a metadata field when it moves to the top"`

---

### Task 8: Changelog and full check

**Files:**
- Modify: `CHANGELOG.md` (repo root, Unreleased)

- [ ] **Step 1: Add the entry** (load the changelog skill), for example:
  "Each metadata filter now shows a checkbox, its current value and a clear button on the field.
  Active filters move to the top of the Metadata section. The filter chips are removed."
- [ ] **Step 2: Run** `make static-checks && make test` in `lightly_studio_view`, then
  `npm run test:e2e-videos`. Expected: all pass.
- [ ] **Step 3: Commit** — `git commit -m "Add changelog entry for metadata field checkboxes"`
- [ ] **Step 4: Hand the branch to Jonas for an end-to-end test.** Slicing into stacked PRs comes
  after his test (see the pull-requests skill).
