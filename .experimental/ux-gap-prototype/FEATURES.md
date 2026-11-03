# UX gap prototype: feature record

<!-- Areas follow the planned PR split. Box editing holds the floating box panel (row 21);
Grid tiles also holds the annotation "Sort by" message (row 19), which sits in the same grid
header. -->

Update this file (and RERUN.md where it applies) in the same commit as each feature change.

Branch `claude/ux-gap-prototype-d56092`, based on `main` at 6d8579dac. Rows refer to
`.experimental/ux-iteration/2026-10-27-friction-log.md`. Run the GUI with
`.experimental/ux-gap-prototype/run_caltech.sh prototype 8001`; RERUN.md has the full checks.

## Annotation source management

- **Settings > Annotation sources.** A tab after Annotation classes, laid out like it. One field
  finds a source or, when none matches, adds it on Enter; the new row is highlighted. Each row
  has a color dot (picker), the name (click or pencil to rename inline; a duplicate name is
  refused with a toast), the annotation count and a trash. Delete confirms with the count and
  warns that evaluation runs using the annotations go out of date. A rename moves the custom
  color and keeps the source the pencil target. Changes save at once. Rows 20, 22. Try: header
  menu, Settings, Annotation sources, type "review_round_2", Enter.
- **Rename a source.** In Settings > Annotation sources, inline. Rows 20, 22. Try: gear on the
  source list, click a name. Commits: 7c3501e6e, 405b4ab41 (first in a filter-panel "..." menu,
  moved to Settings).
- **Delete a source.** The trash in Settings > Annotation sources says how many annotations go,
  then removes the source and its annotations, metadata included. The SDK can delete a source
  too. Rows 20, 22. Try: gear on the source list, trash on a row.
  Commits: c007c8c28, 7c3501e6e, 405b4ab41, 7f07a5c11.
- **Move annotations to another source.** One annotation from the sample details panel (folder
  icon), many from the selection pill on the Annotations grid (Annotate, "Move to annotation
  source…"). IDs, tags and embeddings stay. If the move fails, the annotations stay where they
  were. Rows 22, 23. Try: Annotations grid, edit mode, select tiles, Annotate, "Move to
  annotation source…".
  Commits: 3f7cd598f, d127a1dd4.
- **Drag annotations between sources.** In edit mode each annotation row in sample details has a
  grip; drop it on another source group. Row 23. Try: open a sample with two sources, edit mode,
  drag a row onto the other group. Commits: 8b953f80f.
- **No default source when there are several.** With two or more sources nothing is picked, and
  drawing a box, mask, classification, smart select or find instances refuses with a toast until
  the user picks one. Rows 22, 23. Try: open an image with two sources, draw a box before picking.
  Commits: 4c41f466b.
- **Pencil source picker in the Annotations panel.** Each source row in sample details has a
  pencil; the filled one is where new annotations go. Every source gets a row, also with no
  annotation on the sample, and "New source" adds a name that is created with the first
  annotation. Rows 22, 23. Try: sample details, click the pencil on a source, draw a box.
  Commits: 1fb9dda64.
- **Hidden sources can't take new annotations.** A hidden source shows a crossed-out pencil
  that can't make it the target. Drawing into a hidden target refuses with a toast that says to
  show it. Rows 22, 23. Try: pick a source, hide it with the eye, draw a box.
  Commits: 6e77f3dce, 254060a11.
- **Removed: source picker pill in the sample header.** The "Adding to" pill moved from a corner
  of the canvas (edit mode only) to the sample header. Replaced by the pencil picker in
  1fb9dda64. Rows 22, 23. Commits: c37d516f6.
- **Removed: amber hint above the annotation sources.** A line warned when no target was picked
  or the target was hidden. Dropped because the pencils and the toast on a blocked draw already
  say what to do. Rows 22, 23. Commits: 1fb9dda64 (added), 60b20b12a (removed).

## Selection pill

- **Selection edits live in the pill.** In edit mode the "N selected" pill shows Tag and
  Annotate; outside edit mode it shows only the count and clear. The side panels for selected
  images and selected annotations and the "Assign tag to selection" input in the tag filter are
  gone. Rows 22, 23. Try: Images grid, edit mode, select tiles.
- **Tag popover.** One field finds or creates a tag; each row shows "k/N" with + and × on hover.
  Toasts say "Added 'a' to 9 items" and "Removed 'b' from 3 items". Images and Annotations grids.
  Commits: 23ea42cc4, 9eb0543af.
- **Annotate popover, Images grid.** Pick an annotation source (none is picked when there are
  several; a hidden source is refused), then + adds a classification of a class to every
  selected image and × deletes it after "Delete raccoon from 1 image in ground_truth?". Rows show
  "k/N" for the picked source; a new name offers "Create 'name'". Commits: a408f5ed4.
- **Annotate popover, Annotations grid.** "All N selected", one row per class with its count and
  a trash that deletes those annotations after a confirm, "Relabel all to…" (undo with Ctrl+Z),
  and "Move to annotation source…". Commits: a02c00bd7.
- **T and L open the pill menus.** In edit mode with a selection, T opens Tag and L opens
  Annotate; the pill shows both keys. They do nothing while a text field has focus or outside a
  collection grid. Settings > Shortcuts > Selection rebinds them ("Open tag menu", "Open annotate
  menu"); a key another shortcut uses is refused. Stored in localStorage. Try: Images grid, edit
  mode, select tiles, press T.

## Filter panel

- **One filter list everywhere.** Tags, classes, sources and metadata values share search,
  "Select all", "Clear" and counts. The tag list shows search for any number of tags.
  Rows 16, 36. Try: Images tab, class filter, "Select all", untick car; search the tag list.
  Commits: 2c6a1a2a4, 5ee77e322.
- **One Metadata section.** Width, height, numeric and categorical fields are collapsible fields
  of one style, with active filter chips on top and a field search when there are many. Long
  value lists render 50 rows at a time. Row 17. Try: expand Metadata, open `sequence_id`.
  Commits: 116f6765a, aa97c754f.
- **Metadata value counts match the grid.** Categorical value counts use the same filter as the
  images grid, so they equal the footer. Row 15. Try: select a source, filter `split` =
  labeled, compare the dropdown count with the footer. Commits: 22e8c729e.
- **"No annotations" filter.** A row pinned at the bottom of the Annotations section matches
  images without annotations, with a count lined up with the class counts. Row 29.
  Try: class filter, tick "No annotations". Commits: ccb8f9f48, fed8a60b0.
- **Classes nested under their source.** On the Images and Annotations grids one
  "Annotations" section replaces "Annotation sources" and "Annotation classes". With two or
  more sources each source is a collapsible row with a tri-state checkbox, color dot, count and
  eye, and its classes sit under it. A tick is one exact pair: "deer" under `labels` matches
  only deer in `labels`, not deer in `model_v1`. With one source the class list is flat. Child
  counts are images with that class in that source under the other filters; a source count
  adds up its class counts. The class eye hides the class under every source; the source eye
  hides the source. Each tab keeps its own ticks, and deleting a source drops its ticks.
  Video, frame and caption grids keep the flat class list. Rows 20, 22. Try: after Step f,
  expand `labels` and `model_v1`, tick deer under `labels` only. Commits: e703f7250,
  29a9251f7, c94837430.
- **Filters only.** Source rows have a checkbox and a read-only color dot; class rows have a
  checkbox, a read-only color dot and the eye. Renaming, deleting and coloring sources moved to
  Settings > Annotation sources, opened by the gear in the source list header ("Manage
  annotation sources"). Class colors are set in Settings > Annotation classes. Tags keep their
  "..." menu. Rows 20, 22. Try: Images tab, gear next to "Annotations".
- **Pinned filter panel header.** "Hide filters" stays reachable while the panel scrolls.
  Row 30. Try: scroll the filter panel down, hide it. Commits: b8c3dc7a4.

## State kept across tabs

- **Filters per tab.** Images and Annotations each keep their tags, classes, metadata,
  dimensions, sources and plot selection for the session. Row 27. Try: set a class filter on
  Annotations, go to Images and back. Commits: 58f319661.
- **Last open sample per tab.** Switching back to a tab reopens the sample that was open there.
  Row 28. Try: open an image, switch to Annotations, open an annotation, switch back.
  Commits: ca4bc8c25.
- **Query editor draft.** The typed query and a disabled query survive closing the editor,
  switching panels, opening a sample and switching tabs. Rows 27, 28. Try: type a query, close
  and reopen Query. Commits: 66287a9f1.
- **Embedding plot settings.** Color-by, hidden legend entries and zoom are kept per collection.
  Rows 27, 28. Try: color by a field, zoom, close and reopen the plot. Commits: a6a038d82.
- **Evaluation panel settings.** The open run and its confusion matrix class and color settings
  are kept. Rows 27, 28. Try: open a run, change the matrix, open a sample, come back.
  Commits: bc253e086.
- **Distribution panel settings.** Source, field, count mode, tags, bins and display options
  are kept. Rows 27, 28. Try: pick Percentage in Distr, open a sample, come back.
  Commits: 3d08bb250.

## Export to training

- **Export scope and success toast.** The dialog names the image count and the filtered tags,
  hints to filter by a tag, and confirms a finished export. Row 37. Try: filter by a tag, open
  Export. Commits: ab6412685.
- **Include images in a COCO export.** The zip holds `images/` and `annotations.json` with
  relative file names; the SDK gets `include_images` on `to_coco_object_detections`. Image paths
  stay inside the export folder when local and remote paths mix. Row 38. Try: Export, COCO, tick
  "Include images", download. Commits: 1ca1f3556, bd4e66d51.
- **Export size estimate and 2 GB limit.** The dialog shows the image count and estimated size;
  above 2 GB "Include images" turns off and points to Copy as code. Row 38. Try: Export, COCO,
  read the line under "Include images". Commits: a130eaa7f, 4568201c1.
- **LightlyTrain hand-off.** After an export with images, the success panel shows a copyable
  training snippet and links a new docs page (export, train, predict, add predictions). Row 39.
  Try: download with images, read the success panel. Commits: 2ebdec33b.
- **Copy as code.** The dialog offers the same export as a highlighted LightlyStudio SDK script,
  also with no filter set, kept inside a wider dialog. Rows 37, 38, 39. Try: Export, "Copy as
  code" with one tag filtered. Commits: aeeb68e91, 5325ad2d5, af929442e, fbf52b43a, 5f9f3ea98,
  dd1605125.

## Annotation embeddings

- **Boxes drawn or moved in the GUI get embeddings.** A new or moved box gets a crop embedding in
  the background, so it shows in the annotation plot. Row 34. Try: draw a box, reopen the
  Annotations plot. Commits: acdde381a.
- **Embedding coverage and "Has embedding" filter.** The annotation plot header shows "N of M
  annotations have embeddings", with a filter for annotations with or without one. Row 34.
  Try: Annotations tab, open the plot. Commits: b9bdaae8b.

## SDK loader errors and speed

- **Loader errors name the cause.** An unreadable input file error names the path and the cause.
  Row 6. Try: `add_samples_from_coco` with `annotations_json` ending in `//labels_noisy.json`.
  Commits: 4fdd6f118.
- **Fail fast on missing image files.** Before the loading loop the loader checks a sample of
  image paths spread over the list and names one path it tried; a partly present dataset still
  loads. Row 7. Try: `add_samples_from_coco` with a wrong `images_path`.
  Commits: d9ddc1729, 0351fa52f.
- **Progress bars with totals and step names.** The COCO loader shows a total and ETA, and
  embedding shows one bar per step. Rows 9, 8. Try: a correct `add_samples_from_coco` load.
  Commits: 263878bf0.
- **Faster loads from S3 and hosted Postgres.** COCO image existence checks run in parallel, and
  images and annotations insert in batches of 1024. S3 COCO load went from 9.2 to 161 images/s.
  Rows 8, 40. Try: load the Caltech COCO set from S3; `add_annotations_from_coco` with the
  model_v1 predictions. Commits: ab97bbbcc, b13eb7652, 0b8cd4d8a.
- **`get_sample_by_file_name` and bulk metadata docs.** Look up a sample by file name; the
  metadata docs lead with the bulk `update_metadata` call. Rows 10, 1. Try:
  `dataset.get_sample_by_file_name("<name>.jpg")`; metadata docs page. Commits: ad3782cc8.
- **`ls.utils` and `ls.db_manager` exported.** Pylance no longer flags
  `ls.utils.download_example_dataset(...)`. Row 4. Try: write the call in VS Code.
  Commits: af9bda441.

## Embedding plot

- **Distinct class colors shared by plot and boxes.** A 20-color palette by class order, with an
  Other bucket beyond it. Row 13. Try: color the plot by class, compare with the boxes.
  Commits: 29b43853d.
- **Color by numeric metadata.** Integer and float fields are in Color by, drawn with an inferno
  gradient and a min-max legend bar. Row 18. Try: color by `metadata.hour`.
  Commits: 99e1952ad, b265433a4, 89c34b0e8.
- **Hidden classes stay hidden after a selection.** Row 31. Try: hide a class in the legend,
  then lasso. Commits: 2b8f61241.
- **Rings on grid-selected samples.** Tiles selected in the grid get a ring on their plot point,
  capped at 500. Row 32. Try: tick a few grid tiles with the plot open. Commits: 8bf600454.
- **Removed: ring on the hovered tile's point.** Replaced by rings on the grid selection in
  8bf600454. Row 32. Commits: 5c9adf8c8.
- **Removed: enlarged selected points and their size setting.** Selected and filtered-in points
  were drawn larger, with a size control in the toolbar, then in Settings > Display. Removed
  because Gabriel didn't like the larger points after trying them; row 33 stays open.
  Commits: 1bf29d55e, 4df148d19, ce31c4cd1, f0ae032b7 (built), f424f2346 (removed).

## Sample navigation

- **Next and previous follow the grid.** In the sample view, arrows follow the embedding plot
  selection and the similarity order, on both Images and Annotations. Row 26. Try: Annotations
  tab, text search, open result 2, press right arrow. Commits: d69f7f2b7, 09c980d1c.
- **Preloaded next and previous images.** The image view preloads the next 3 and the previous
  image. Row 11. Try: press right arrow through a few S3 images. Commits: 5e6e865c6.

## Grid tiles

- **"Show on tiles" menu.** Pick classes, single tags, sources and metadata fields to show as
  chips on each tile, with search and group headers. Each chip kind has its own look and a fixed
  order, and the menu shows the same markers. Row 12. Try: grid header, "Show on tiles", tick a
  tag, a source and `camera`. Commits: 17a4dccbe, 58a4db970, 152756935, 6e0471f64.
- **Class on annotation tiles by default.** The class chip is on until the user changes "Show
  on tiles". Rows 12, 13. Try: open the Annotations grid. Commits: 4a5a523c3.
- **"Sort by" message on annotations.** With no evaluation metrics the dropdown says to run an
  evaluation. Row 19. Try: Annotations tab, no evaluation, open "Sort by". Commits: 5969bb86e.
- **Removed: class name in the similarity badge.** Annotation tiles showed the class next to the
  score. Removed because the class chip is on by default and the badge repeated it. Row 13.
  Commits: 29b43853d (added), cb7f930e3 (removed).

## Box editing

- **Drawn box stays on screen.** A new box doesn't vanish while it saves. Row 25. Try: draw a
  box. Commits: aa38e7de1.
- **Floating panel beside the selected box.** Class, source and delete sit next to the selected
  box in the image sample view. Row 21. Try: edit mode, select a box. Commits: 5f1620a2f.

## Self-hosted branch ux-gap/onboarding-card

In lightly-studio-self-hosted, not this repo.

- **Quickstart load scripts and guide link** in the onboarding card. Row 2. Commits: 2c59e56.
- **Highlighted code snippets** in the onboarding card. Row 3. Commits: f5255ca.
- **LightlyStudio favicon.** Row 5. Commits: 965983c.

Tooling and test-only commits, no feature entry: a60577320, 53fcb016b, ed13c7583, 50cebad9e,
028d7d0aa, 3b8aa52b4.
