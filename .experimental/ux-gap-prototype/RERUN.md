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
| 17 | Open the Metadata filters | One section, one style; no "Add categorical metadata field" button |
| 16 | Find a tag in the tag filter | Search box in the tag list |
| 36 | Filter all classes except car | "Select all", then untick car |
| 30 | Scroll the filter panel down, then hide it | Header stays pinned |
| 12 | Grid header, "Show on tiles": tick classes, tags, `camera` | Chips on tiles; Annotations grid has its own choice |
| 13 | Color the plot by class; text search "dog" on Annotations | 16 distinct colors that match the boxes; class name in each score chip |
| 18 | Color the plot by `metadata.hour` | Gradient bar 0 to 23 |
| 31 | Hide one class in the legend, then lasso | It stays hidden |
| 33 | Lasso some points | Selected points bigger; -/Auto/+ size control |
| 32 | Hover a grid tile | White ring on its plot point |
| 34 | Annotations tab plot | Header says "N of M annotations have embeddings" when N < M; "Has embedding" filter |
| 26 | Annotations tab: text search, open result 2, press right arrow | Goes to result 3. Same on Images with a lasso selection |
| 27 | Set a class filter on Annotations, go to Images and back | Each tab keeps its own filters |
| 28 | Open an image, switch to Annotations, open an annotation, switch back | The same image is open |
| 19 | Annotations tab, no evaluation, open "Sort by" | Message: "Run an evaluation to sort by its metrics." |
| 20, 22 | Source list: "..." menu, Rename, then Delete | Source renamed; delete says how many annotations go, then the source is gone |

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
| 11 | Press right arrow through a few images | Next image shows at once |
| 34 | Reopen the Annotations plot | The new box is a point |

### Step e: export and train v1

| Row | Do | Prototype should |
|---|---|---|
| 37 | Filter by tag `to_label`, open Export | "Exports the N images ... in tag to_label"; success toast |
| 38 | COCO, tick "Include images", download | Zip with `images/` and `annotations.json`, relative `file_name`s |
| 39 | After the download | LightlyTrain snippet with "Copy code" and a docs link |

Training itself stays on compute-03 and is not timed here.

### Step f: import predictions

Run `import_predictions.py` as in Setup. Check that `model_v1` shows next to `labels`, and that
the Annotations plot counts the new boxes.

### Step h: autolabel

| Row | Do | Prototype should |
|---|---|---|
| 23 | Sample view: folder icon next to copy, on a `model_v1` box | Box moves to `labels`, keeps its embedding |
| 22, 23 | Annotations grid, edit mode, select `model_v1` tiles, "Move to annotation source" | Tiles leave the grid; they show under `labels` |

Time 4 images fixed from predictions against 4 labeled from scratch, as in the original step.

### Step 0: load from S3 (last, needs the `lightly` AWS profile)

| Row | Do | Prototype should |
|---|---|---|
| 6 | `add_samples_from_coco` with `annotations_json` ending in `//labels_noisy.json` | Error names the path and the cause |
| 7 | Same with a wrong `images_path` | Fails in seconds, names one full path it tried |
| 9, 8 | A correct load | One bar per step with a total: Loading images, Loading annotations, Embedding images, Embedding annotations |
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
24 (metadata editing, already on track), 2, 3, 5 (hosted onboarding card, separate branch in
lightly-studio-self-hosted), 8, 40 (loader speed, later).
