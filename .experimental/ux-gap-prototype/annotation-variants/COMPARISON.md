# Where do new annotations go? Main, pencil, radio

Task: add a deer box to `model_v2` on one image. The dataset has 8 annotation sources.

| | main today | prototype: pencil | variant C: radio |
|---|---|---|---|
| Before the first box | Preset to the first source (`labels`). You are not asked. | Nothing is picked. Nothing says so. | "Pick where new annotations go." in amber above the sources |
| Box before a pick | Goes to `labels` | Refused with a toast | Refused with a toast |
| How you pick | "Adding to" pill on the canvas | Pencil on a source group | Radio on a source group |
| Where the target shows | The pill, with the name cut to "mod…" | A filled pencil | A selected radio and "New annotations go here" |
| Classification "+" | No hint | No hint | "Adds to model_v2" |
| Outside edit mode | The pill is hidden | The pencils show | The radios are hidden |

Images: `side-by-side-<step>.png` (full window) and `panel-<step>.png` (close-up), steps 1 to 5.
GIFs: `main.gif`, `pencil.gif`, `radio.gif`.

## Open questions

1. Is a radio clear enough without the "New annotations go here" text?
2. Main presets a source and the prototype does not. Is "you must pick" correct when one
   source is clearly the ground truth?
3. The radio is in the panel, but the box tools are on the canvas. Is the distance a problem
   with 8 sources, when the target can scroll out of view?
