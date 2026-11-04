# Annotation card: GUI check

Date: 2026-11-04. Build: `3ebed4832` frontend (`make build-dirty`), served by `serve.py` on port
8014 from `~/data/caltech-ux-run-dbs/demo-card.db`, a copy of `demo-variants.db`. Browser
viewport 1400x900. `lightlyStudio_*` storage keys cleared first. Screenshots are in `card-gui/`.

Static checks: `make static-checks` clean (svelte-check 0 errors). Unit tests: `npx vitest run`
4452/4452 after the Task 11 fix.

| # | Check | Result | Screenshots |
|---|---|---|---|
| 1 | First box with no class: card at the box, input focused, Esc drops it and no create request reaches the server. Pick `deer`: saved, card at the box. Next box saves as `deer` with no prompt. Next image: no card, chip keeps `labels` / `deer`. | Pass | `1a`–`1e` |
| 2 | Relabel by typing (`coy` + Enter → coyote), then by the recent chip (`deer`). The chip follows each pick. | Pass | `2a`, `2b` |
| 3 | Move a `review_round_2` box to `labels` from the card. Toast "Moved 1 annotation to labels"; the card shows `labels`; the chip target is unchanged. | Pass | `3a`, `3b` |
| 4 | Delete the selected box with the Delete key; the card closes. Cmd+Z after that brings it back. | Pass | `4a`, `4b` |
| 5 | Brush a mask: it takes the sticky class. Relabel the mask from the card (card anchored at the mask bounds). Deselect, draw a box: it gets the chip's class; the card flips left near the edge. | Pass | `5a`, `5b` |
| 6 | Hold `v`: the annotations and the card hide (card `visibility: hidden`); release brings both back with the selection kept. | Pass | `6` |
| 7 | Collapse all hides the rows and keeps the source headers and radios; Expand all restores them. | Pass | `7` |
| 8 | Mark `labels` as Default in Settings, open a new tab, enter edit mode: the chip shows `labels`, and `lightlyStudio_last_annotation_source` stays `{}`. | Pass | `8a`, `8b` |

Also checked: the pending card ignores shortcut letters typed into it (typing `deer` left the
box tool on and edit mode open). With nothing selected, `k` opens the chip's class list with `k`
in a focused input.

## Observations

- One `labels` box (`a751a3ad`, created as `deer`) later read `car` and was then deleted. The
  browser sent no request for it: its only writes were 2 creates, 2 relabels of a different box
  (`1482622b`) and 1 move. Unexplained; possibly another client on port 8014.
- Clicking a selected box deselects it. Two quick clicks look like "selection does nothing".
- While the card is open, the other annotations are not drawn.
- The side panel's scroll container sits 4px scrolled sideways after Collapse all.
- The chip's class popover is see-through over a bright image.
- Once, a drag in the box tool reflowed the canvas and created no box; the next drag worked.
