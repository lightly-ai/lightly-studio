# Embedding plot: ask before computing above 250k (STU-102)

## Why

The first PaCMAP compute of the embedding plot looks the same as loading a cached plot. On one
customer's tenant, 2M points took 38 min with no sign that anything was happening. Above 250k
embeddings, the panel must ask before it starts, and while it computes it must say so.

## Goals

1. The frontend knows whether a usable plot is saved and how many embeddings the collection has.
2. With no usable plot and `>= 250_000` embeddings, the panel shows a Compute prompt and sends no
   plot request until the user clicks Compute.
3. While the plot computes, the panel says "Computing plot…" with a running timer. Loading a saved
   plot keeps today's "Loading embeddings data..." state.
4. Below 250k, the panel starts the compute on its own, as today, but shows the computing state.

## Non-goals

- Showing an outdated plot with a Recompute banner. That is the follow-up ticket (see Follow-up).
- Faster PaCMAP, or the GUI freeze during compute (LIG-11581).
- Grid region filters that recompute a dirty plot (`embedding_region_resolver` calls
  `get_twodim_embeddings`). Unchanged here.
- Remembering a running compute across a page reload.

## Anti-goals

- Any mention of text axes in the prompt or the computing state (review feedback: focus on the one
  thing, the 2D compute).
- A prompt for a saved, clean plot, or for collections below 250k.

## Approaches

1. **New status endpoint (picked).** The panel first asks whether the plot is saved and how many
   embeddings there are, then gates the plot request on the answer. The plot endpoint stays as it
   is. Costs one small extra request per panel open.
2. **`compute: false` flag on the plot endpoint**, answered with a 409 and the count. Rejected:
   an error code drives normal flow, and default view, filters and color-by all need the flag.

## Design

### Backend

Add a read-only route next to the plot route in
`lightly_studio/src/lightly_studio/api/routes/api/embeddings2d.py`:

```
GET /collections/{collection_id}/embeddings2d/status
-> { "is_computed": bool, "embedding_count": int }
```

- `is_computed` is true when the `embedding_plot` row for (collection, default embedding model)
  exists and `is_dirty` is false. Missing, dirty, and the placeholder row from `mark_dirty`
  (empty `data`, dirty) all mean false.
- Select only `is_dirty`. Never load the `data` column: on a 2M plot it is the whole Arrow blob.
- `embedding_count` is the number of `sample_embedding` rows for the default embedding model whose
  sample is in the collection. This is what PaCMAP runs on, not the filtered count.
- Same 404 as the plot route for an unknown collection. No default embedding model: follow the
  plot route's current behavior.

### Frontend

- A status query hook next to `useEmbeddings`. `useEmbeddings` gains an `enabled` flag.
- The plot request is enabled when the layout is text axes (no PaCMAP), or `is_computed`, or
  `embedding_count < 250_000`, or the user clicked Compute.
- The threshold is a frontend constant, `250_000`, compared with `>=`.
- After the plot request succeeds, refetch the status.
- Panel states, picked from the status and the plot query:

| Status | Plot request | Panel shows |
|---|---|---|
| not computed, `>= 250k`, no click | off | Compute prompt |
| not computed | in flight | Computing state with timer |
| computed | in flight | today's loading state |
| any | done | the plot |

### UI

Both states are centered in the black plot area, as in the mock (`PlotComputePrompt`):

- **Compute prompt:** scatter icon, "Plot not computed", "{count} {items}. The first compute can
  take several minutes.", primary button "Compute plot". `{items}` is the plural item label of the
  collection: images, videos, annotations or sequences.
- **Computing:** spinning loader, "Computing plot…", "Running for {m:ss}. The first compute can
  take several minutes."

The timer counts from when the compute request started, on the client. It resets on reload.
Closing and reopening the panel mid-compute keeps the computing state for the same tab session.

## Edge cases to test

- 249k embeddings with a clean plot, then 1k added: the plot turns dirty, the count is 250k, the
  prompt shows.
- Exactly 250,000 embeddings with no plot: prompt shows.
- 249,999 with no plot: no prompt, computing state shows.
- Clean plot above 250k: no prompt, normal loading.
- Text axes layout above 250k with no plot: plot renders, no prompt.

Accepted window: the panel decides on a status read before the plot request. If an embedding
write turns a clean plot dirty after that status read, the next plot request (a filter, color-by
or layout change while the panel stays open) rebuilds the plot without the prompt. The status
refetches on window focus and after each plot load, which narrows the window. Closing it needs a
server-side guard on the plot route, which this design does not add.

## Left to the builder

- Query shape for `embedding_count` on Postgres and DuckDB, and whether it needs an index at 2M.
- File split and naming for the status hook and `PlotComputePrompt`, per `frontend-guide`.
- Delete the throwaway mock first: `PlotStatusBanner/`, `PlotComputePrompt/` and the `plotMock`
  lines in `PlotPanel.svelte`. Rebuild `PlotComputePrompt` properly.

## Follow-up (separate ticket)

Show an outdated plot with a banner above it ("Plot is outdated", "{n} images added since the
last compute", Recompute button), and "Recomputing plot…" with the timer while it runs. The old
plot stays usable. Mock: `3-outdated-panel.png` and `4-recomputing-panel.png`. Includes the grid
region filter reading the old plot, and points for deleted samples on the old plot.
