# Annotation source picker: variants

The same task in every column: add a deer box to `model_v2` on sample 1 of 5000 (Caltech demo
data, 8 annotation sources).

| Column | What picks the source | URL param |
|---|---|---|
| main today | "Adding to" pill on the canvas, preset to the first source | none, `main` build |
| prototype: pencil | A pencil on each source group in the Annotations panel | `?annotateVariant=pencil` (default) |
| variant C: radio | A radio on each source group, "New annotations go here" on the picked one | `?annotateVariant=radio` |

The switch keeps the last value in localStorage. To go back, open a URL with
`?annotateVariant=pencil`.

## Files

- `side-by-side-<step>.png`: the full window of the three columns at steps 1 to 5.
- `panel-<step>.png`: the Annotations panel of the three columns at 2x, for a close look.
- `main.gif`, `pencil.gif`, `radio.gif`: the steps of one column, 2 s per frame.
- `shots/` (not committed): the single 2880x1800 screenshots. Run `capture.cjs` to make them.
- `capture.cjs`, `side_by_side.py`: the scripts that make the files above.
- `COMPARISON.md`: one page to send with the images.

## What to try

**main today** (port 8015)

1. Open a sample and click Edit. The pill in the lower-left corner of the canvas says "Adding to labels".
2. Draw a box. The box goes to `labels`. You did not pick this source.
3. Open the pill and pick `model_v2`. The pill shows "mod…", because the name is cut.
4. Draw a box again. It goes to `model_v2`.
5. Look for the target in the Annotations panel. The panel does not show it.

**prototype: pencil** (port 8016, `?annotateVariant=pencil`)

1. Open a sample. The pencils show also before you click Edit.
2. Click Edit and draw a box. A toast refuses the box and tells you to use the pencil.
3. Click the pencil on `model_v2`. A pencil next to a name usually means "rename".
4. Draw a box. It goes to `model_v2`.
5. Scroll to Classification. The "+" does not show which source it adds to.

**variant C: radio** (port 8014, `?annotateVariant=radio`)

1. Open a sample. There are no radios before you click Edit.
2. Click Edit. The panel says "Pick where new annotations go." above amber radios.
3. Click the radio on `model_v2`. The group says "New annotations go here".
4. Draw a box. It goes to `model_v2`.
5. Scroll to Classification. The text under "+" says "Adds to model_v2".

## Serve the three columns

Each column uses its own copy of `~/data/caltech-ux-run-dbs/demo.db`. Copy the `.wal` file too.
Stop a server with Ctrl-C, not `kill -9`, because DuckDB can damage its indexes.

```bash
cd ~/data/caltech-ux-run-dbs
for name in demo-main-baseline demo-variants-pencil demo-variants; do
    cp demo.db $name.db && cp demo.db.wal $name.db.wal
done
```

```bash
# main: the detached main worktree, built on 2026-10-29 (6d8579dac)
cd .claude/worktrees/ux-baseline-main/lightly_studio
../.venv/bin/python <this-worktree>/.experimental/ux-gap-prototype/serve.py \
    --db ~/data/caltech-ux-run-dbs/demo-main-baseline.db --port 8015
```

```bash
# pencil and radio: this branch, after `make build-dirty-lightly_studio_view`
cd <this-worktree>/lightly_studio
../.venv/bin/python ../.experimental/ux-gap-prototype/serve.py \
    --db ~/data/caltech-ux-run-dbs/demo-variants-pencil.db --port 8016
../.venv/bin/python ../.experimental/ux-gap-prototype/serve.py \
    --db ~/data/caltech-ux-run-dbs/demo-variants.db --port 8014
```

Then make the images again:

```bash
cd <this-worktree>/lightly_studio_view
NODE_PATH=node_modules node ../.experimental/ux-gap-prototype/annotation-variants/capture.cjs
python3 ../.experimental/ux-gap-prototype/annotation-variants/side_by_side.py
```

## Remove the losing variant

The radio code is in `AnnotationTargetRadio`, `AnnotationTargetHint`, `AnnotationTargetCaption`
and `useAnnotateVariant`. `AnnotationTargetControl` selects the variant. To keep one variant,
delete the other folders and put that variant's component in place of `AnnotationTargetControl`.
