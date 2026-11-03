# Design: filters only filter, edits move to the selection pill and Settings

2026-11-03 · Prototype branch `claude/ux-gap-prototype-d56092` · Slack thread in #C09MGSC2JLQ
(Jonas's proposal, 3 Nov recording) · Builds on Michal's Annotation classes tab (LIG-11319, on main)

## Why

The filter panel mixes filtering with editing: assigning tags, renaming and deleting sources,
picking colors. Igor and Jonas agreed in the thread to keep the panel "a clean filtering unit"
and to run every action on a selection from one place, as Linear does with its selection pill.
Igor asked to test the result hands-on with 2 to 3 teammates (Nick, Lionel, Joel or Shania),
who use it themselves rather than watch a demo.

This is a prototype for that test, not production PRs. Prototype rules apply: it runs, passes
static checks and the touched tests, survives a full workflow run, and has no schema change.

## Decisions

Made in the brainstorm on 2026-11-03:

1. The selection pill gets Tag and Annotate, both only in edit mode, as in Jonas's video.
2. Tag assign and remove move to the pill. Tag rename and delete stay in the filter panel.
3. Today's edit-mode panels go: `SelectedAnnotations` (relabel, move, delete) and
   `BulkClassificationPanel`. Move to annotation source joins the Annotate popover.
4. A new Settings tab, Annotation sources: create, rename, delete with annotation count, color.
5. Color pickers leave the filter panel (sources and classes). The eye toggles stay.
6. Classes nest under their annotation source in the filter panel. A tick means an exact
   (source, class) pair.
7. A source checkbox ticks all its classes and shows a partial state when some are ticked.
8. With one source, the class list stays flat.
9. Shortcuts: T opens Tag, L opens Annotate (A is the SLIC tool). They can be rebound.
10. Annotations grid: the popover's top rows show what is selected, and a separate "Relabel all
    to…" field picks the target. This differs from the video, where clicking a row relabels.

*My call, flagged for review:* the T and L bindings live in localStorage, not in the settings
table. Every shortcut is a column of `SettingTable`, so a database-backed binding is a schema
change. The prototype's plot point size setting set the precedent.

## Slice 1: selection pill

`SelectionPill` (mounted in the collection `+layout.svelte`) shows "N selected" and a clear
button. In edit mode it also shows **Tag** and **Annotate**, each with its shortcut hint. Out of
edit mode it is unchanged.

### Tag popover (Images and Annotations grids)

- One field finds or creates. A name with no match offers "Create 'name'", which creates the
  tag and assigns it to the selection.
- Each row shows the tag and "k/N": how many selected items have it.
- On hover, **+** adds the tag to every selected item (shown when k < N) and **×** removes it
  from every selected item (shown when k > 0).
- The list scrolls after 5 rows.
- Toasts: "Added 'a' to 9 items", "Removed 'b' from 3 items".
- It works on samples in the Images grid and annotation crops in the Annotations grid, as
  `TagAssignInput` does today by `gridType`.

### Annotate popover, Images grid (classifications)

- Annotation source picker at the top. It follows the prototype's rules: no default when there
  are several sources, and hidden sources cannot be the target.
- Find-or-create field for the class, then a row per class with "k/N".
- **+** adds a classification of that class, in that source, to every selected image that lacks
  one.
- **×** deletes the classifications of that class in that source from the selection, after a
  confirm: "Delete raccoon from 1 image in ground_truth?"

### Annotate popover, Annotations grid

- Header "All N selected", then one row per class present in the selection with its count and a
  trash icon. The trash deletes those annotations after a confirm with the count.
- "Relabel all to…" finds or creates a class and relabels every selected annotation to it
  (main's `useBulkRelabelAnnotations`).
- Footer "Move to annotation source…" opens the existing `AnnotationSourcePicker` and calls
  `useMoveAnnotationsToSource`.

### Shortcuts

T and L open the popovers on a grid with a non-empty selection in edit mode, and do nothing
when a text field has focus. Settings > Shortcuts lists both and can rebind them; the binding is
stored in localStorage.

### Removed

- `lib/components/AnnotationsGrid/SelectedAnnotations` and its mount in `AnnotationsGrid.svelte`.
- `lib/components/BulkClassificationPanel` and its mount in `Images.svelte`.
- The "Assign tag to selection" input in `TagsMenu`.

### Backend

Existing: tag add by IDs and by filter, tag remove by IDs, classification bulk create, bulk
delete and bulk relabel, each by IDs and by filter.

New:

```text
POST   /collections/{id}/tags/counts                  tag counts for a selection (IDs or filter)
DELETE /collections/{id}/tags/{tag_id}/remove/samples_by_filter
POST   /collections/{id}/annotations/classifications/delete_for_samples
POST   /collections/{id}/annotations/label_counts     class counts of an annotation selection
```

The tag counts cover samples on the Images grid and annotation crops on the Annotations grid.

`delete_for_samples` is needed because `AnnotationsFilter.sample_ids` holds annotation IDs, so
no existing filter scopes a delete to parent images.

The class "k/N" on the Images grid uses the existing image annotation counts with
`count_mode: samples`. They already restrict to given sources
(`annotation_count_helpers/restrict_to_annotation_sources.py`), and `SampleFilter.sample_ids`
takes an ID selection.

## Slice 2: Settings > Annotation sources

A tab after Annotation classes, laid out like it (`lib/components/Settings/AnnotationClassesTab`).

1. **Find or add.** One field filters the list. Enter adds a source only when no source matches.
2. **Rows.** Color dot (picker), name (click to rename inline), annotation count, trash. A new
   source is highlighted and scrolled into view. A duplicate name shows an error.
3. **Delete** confirms with the annotation count and warns that evaluation runs using them become
   stale. It reuses the prototype's source delete, which also removes annotation metadata.
4. Changes save at once; the footer says so, as on the classes tab.
5. **Colors** use the same in-memory store as today (`useCustomLabelColors`), keyed by name. A
   rename moves the color. Colors still reset on reload.

The filter panel after this slice:

- Tags: checkbox and the "…" menu with Rename and Delete.
- Sources and classes: checkbox, read-only color dot, eye toggle. No "…" menu, no color picker.
- A gear in the annotations section header opens Settings on the Annotation sources tab.

### Backend

```text
GET  /collections/{id}/annotation_collections_with_counts
POST /collections/{id}/annotation_collections          body: {name}
```

The POST uses `collection_resolver.get_or_create_child_collection`, the same resolver that
creates a source lazily when its first annotation is saved.

## Slice 3: nested source and class filter

Applies to the Images and Annotations grids, where the source list shows today. Video, video
frame and caption grids keep the flat class list.

- With two or more sources, one "Annotations" section replaces "Annotation sources" and
  "Annotation classes". Each source is a collapsible parent row with a tri-state checkbox, color
  dot, image count and eye. Its classes are child rows with checkbox, color dot, count and eye.
- With one source, the class list is flat, as today. The parent row appears once a second
  source exists.
- "No annotations" stays pinned at the bottom.
- A child count is the number of images with that class in that source, under the other filters.
- The class eye hides the class in every source and shows the same state under each source. The
  source eye hides the whole source.
- Nothing ticked means no annotation filter.

### State

A set of (source ID, class ID) pairs replaces today's ticked source IDs
(`useAnnotationCollectionsFilter`) and ticked class IDs (`selectedAnnotationFilterIds`). It
follows the prototype's per-tab filter state.

### Backend

1. `AnnotationsFilter` (`resolvers/annotations/annotations_filter.py`) gains
   `source_label_pairs`. A sample matches when one of its annotations matches any pair, on the
   same annotation row. The existing `collection_ids` and `annotation_label_ids` fields stay for
   other callers.
2. The image annotation count (`resolvers/image_resolver/count_image_annotations_by_collection.py`)
   groups by source and class, not by class name only.

### Callers to update

- Grid requests (`Images.svelte`, `AnnotationsGrid.svelte`) and count requests (`+layout.svelte`).
- The prototype's export scope text and "Copy as code". Check first whether the SDK query can
  express pairs. If it cannot, "Copy as code" refuses with a message instead of exporting a
  different set.

## Build order

Slice 1, then slices 2 and 3. Slice 1 touches the grids and the pill. Slices 2 and 3 both edit the
filter panel, so slice 2 lands before slice 3. Slices 1 and 2 can run in parallel worktrees.

For every slice: update `.experimental/ux-gap-prototype/FEATURES.md`, and RERUN.md where a check
changes, in the same commit as the feature.

## Testing

- Slice 1: vitest for each popover (add, remove, create, counts, confirm on delete, edit mode
  gating, T and L, no shortcut while typing). Pytest for the two new tag endpoints.
- Slice 2: vitest mirroring `AnnotationClassesTab.test.ts` (find or add, rename, duplicate name,
  delete, color). Pytest for the two new source endpoints.
- Slice 3: pytest for the pair filter (one pair, two pairs, a mismatched pair excluded) and the
  per-source counts. Vitest for the tree (tri-state parent, flat with one source, shared class
  eye, nothing ticked).
- Then a GUI run on `~/data/caltech-ux-run-dbs/prototype.db` (ground truth plus model_v1), and
  the hands-on test with 2 to 3 teammates.

## Out of scope

- A command palette. T and L only.
- Saving colors in the database.
- Role checks on the Settings tab, as on the classes tab.
- Tag rename and delete in Settings.
