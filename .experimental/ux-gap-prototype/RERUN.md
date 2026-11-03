# Rerun checklist: UX gap prototype vs main

Goal: check whether the prototype removes the friction rows from the 2026-10-27 run. Friction log:
`/Users/gabrielfruet/dev/lightly/lightly-studio/.experimental/ux-iteration/2026-10-27-friction-log.md`.

## Setup

Both builds run on this Mac with the same data, loaded by the same script.

Baseline, `main` at 6d8579dac (worktree `.claude/worktrees/ux-baseline-main`), port 8002:

```bash
.experimental/ux-gap-prototype/run_caltech.sh main 8002 /Users/gabrielfruet/dev/lightly/lightly-studio/.claude/worktrees/ux-baseline-main
```

Prototype, this branch, port 8001:

```bash
.experimental/ux-gap-prototype/run_caltech.sh prototype 8001
```

Run the commands from the prototype worktree root. The first run per build takes about 15 minutes
(GUI build plus load and embed). Databases: `~/data/caltech-ux-run-dbs/{main,prototype}.db`.
Add `--reload` as the 4th argument to start from fresh data before each run.

Step f needs the predictions. Stop the GUI first (DuckDB allows one writer), then:

```bash
cd lightly_studio && uv run python ../.experimental/ux-gap-prototype/import_predictions.py --db ~/data/caltech-ux-run-dbs/prototype.db
```

For the baseline, run the same command from the main worktree's `lightly_studio` with `main.db`.

## Rules

1. Run `main` first, then the prototype. The second run is the practiced one, so the row result
   counts more than the minutes.
2. GUI first; the SDK only where the step says so.
3. For each row, write "still happens" or "gone", and the minutes for each step.

## Checks per step

### Step a: explore

| Row | Do | Prototype should |
|---|---|---|
| 15 | Select a source, filter metadata `split` = labeled | Dropdown count equals the footer (1,502) |
| 17 | Open the Metadata filters, expand `sequence_id` | One section, one style; no "Add categorical metadata field" button; 50 values, then "Show 50 more" |
| 16 | Find a tag in the tag filter | Search box in the tag list, even with 1 tag |
| 36 | Filter all classes except car | "Select all", then untick car |
| 30 | Scroll the filter panel down, then hide it | Header stays pinned |
| 12 | Grid header, "Show on tiles": search, tick one tag, the `model_v1` source, `camera` | Chips on tiles ("model_v1: 2 deer"); annotation tiles show their class by default |
| 13 | Color the plot by class; text search "dog" on Annotations | 16 distinct colors that match the boxes; class chip on each tile, once |
| 18 | Color the plot by `metadata.hour` | Inferno gradient bar 0 to 23 |
| 31 | Hide one class in the legend, then lasso | It stays hidden |
| 32 | Tick a few grid tiles | White rings on their plot points |
| 34 | Annotations tab plot | Header says "N of M annotations have embeddings" when N < M; "Has embedding" filter |
| 26 | Annotations tab: text search, open result 2, press right arrow | Goes to result 3. Same on Images with a lasso selection |
| 27 | Set a class filter on Annotations, go to Images and back; type a query, close and reopen Query; pick Percentage in Distr, open a sample | Each tab keeps its own filters; query text, plot color-by, eval run and Distr settings stay |
| 28 | Open an image, switch to Annotations, open an annotation, switch back | The same image is open |
| 19 | Annotations tab, no evaluation, open "Sort by" | Message: "Run an evaluation to sort by its metrics." |
| 20, 22 | Source list: gear ("Manage annotation sources"); in Settings > Annotation sources rename a source, then delete it; type "review_round_2", Enter | Settings opens on Annotation sources; no "..." or color picker on filter rows; source renamed; delete says how many annotations go and warns about evaluation runs, then the source is gone; the new source is highlighted |

### Step b: curate

| Row | Do | Prototype should |
|---|---|---|
| 29 | Class filter, tick "No annotations" | Only images without boxes (3,600 on fresh data) |

Then tag about 100 of them `to_label`, as in the original step.

### Step c: label (time 4 images by hand)

| Row | Do | Prototype should |
|---|---|---|
| 25 | Draw a box | It stays on screen while it saves |
| 21 | Edit mode, select a box | Panel beside it: class, source, delete |
| 22 | Open an image with two sources, draw a box before picking; click the pencil on a source in the Annotations panel, then hide that source with its eye and draw again | No pencil is filled at first; the first draw shows "Pick a source with the pencil in the Annotations panel..." and creates nothing. The hidden source shows a crossed-out pencil; drawing shows "... is hidden. Show it ..." and creates nothing. No hint line above the sources |
| 11 | Press right arrow through a few images | Next image shows at once |
| 34 | Reopen the Annotations plot | The new box is a point |

### Step e: export and train v1

| Row | Do | Prototype should |
|---|---|---|
| 37 | Filter by tag `to_label`, open Export | "Exports the N images ... in tag to_label"; success toast |
| 38 | COCO, tick "Include images", download | Size shown under the option ("5,000 images, about 2 GB"); zip with `images/` and `annotations.json`, relative `file_name`s. Above 2 GB the option turns off and points to Copy as code |
| 39 | After the download; then "Copy as code" with one tag filtered | LightlyTrain snippet with "Copy code" and a docs link; an SDK script for the same export (edit its `.db` path) |

Training itself stays on compute-03 and is not timed here.

### Step f: import predictions

Run `import_predictions.py` as in Setup. Check that `model_v1` shows next to `labels`, and that
the Annotations plot counts the new boxes.

### Step h: autolabel

| Row | Do | Prototype should |
|---|---|---|
| 23 | Sample view, edit mode: drag a `model_v1` row's grip onto the `labels` group (or use the folder icon) | Box moves to `labels`, keeps its embedding |
| 22, 23 | Annotations grid, edit mode off, select `model_v1` tiles, pill: Annotate, "Move to annotation source…" | Tiles leave the grid; they show under `labels`. No selected-annotations side panel |
| 22, 23 | Images grid, edit mode off, nothing selected; then select 3 tiles, press T, then L; type in the search box and press T | The dashed hint names T and L; with a selection T opens Tag, L opens Annotate (classifications, "k/N" per class); T typed in a field only types |
| 22 | Images grid, tick 2 tiles; open ⋯; click "Select all N" | Pill shows 2 thumbnails, "Select all N" with the footer count; ⋯ has "Copy IDs"; after select-all the link and ⋯ go away |
| 22 | Images grid, select tiles, L, "Choose source" → `labels`; close, reopen with L, press 2; type `c2` in the search | Header says "Add to labels" on reopen (remembered); 2 adds the second class with its badge; `c2` only searches |

Time 4 images fixed from predictions against 4 labeled from scratch, as in the original step.

### Step 0: load from S3 (last, needs the `lightly` AWS profile)

| Row | Do | Prototype should |
|---|---|---|
| 6 | `add_samples_from_coco` with `annotations_json` ending in `//labels_noisy.json` | Error names the path and the cause |
| 7 | Same with a wrong `images_path` | Fails in seconds, names one full path it tried |
| 9, 8 | A correct load | One bar per step with a total; images load at ~150/s from S3, not 8 |
| 40 | `add_annotations_from_coco` with the model_v1 predictions | Seconds, not 5 minutes |
| 10, 1 | `dataset.get_sample_by_file_name("<name>.jpg")`; metadata docs page | Works; docs lead with `update_metadata` |
| 4 | `ls.utils.download_example_dataset` in VS Code | No Pylance error |

## Timing

| Step | main minutes | prototype minutes | main finished without help? | prototype finished without help? |
|---|---|---|---|---|
| a Explore | | | | |
| b Curate | | | | |
| c Label (4 by hand) | | | | |
| e Export | | | | |
| f Import predictions | | | | |
| h Autolabel (4 + 4) | | | | |
| 0 Load from S3 | | | | |

## Not in the prototype

14, 41 (few-shot classifier and evaluation on annotations), 35 (query editor on annotations),
24 (metadata editing, already on track), 33 (larger selected points: built, then removed after
trying it). Rows 2, 3, 5 (hosted onboarding card) are on branch `ux-gap/onboarding-card` in
lightly-studio-self-hosted, worktree `../lightly-studio-self-hosted-worktrees/ux-gap-onboarding`,
not in this local build.
