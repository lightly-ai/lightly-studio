# Embedding Plot Compute Prompt Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Above 250k embeddings with no usable plot, the embedding plot panel asks before it computes, and while it computes it says so with a running timer.

**Architecture:** A new read-only status route tells the frontend whether the plot is saved and how many embeddings there are. A pure gate function picks the panel view from that status, and the plot request is enabled only when the gate allows it. A centered `PlotComputePrompt` renders the prompt and the computing state.

**Tech Stack:** FastAPI, SQLModel, pytest (backend); SvelteKit, Svelte 5, TanStack Query, vitest (frontend).

**Spec:** `.experimental/superpowers/specs/2026-11-16-embedding-plot-compute-prompt-design.md`

## Global Constraints

- Threshold: prompt when `embedding_count >= 250_000` and the plot is not computed.
- "Computed" means the `embedding_plot` row exists and `is_dirty` is false. Missing, dirty and placeholder rows are not computed.
- Never load `EmbeddingPlotTable.data` in the status path.
- No mention of text axes in any new copy.
- Copy, exact: "Plot not computed", "{count} {items}. The first compute can take several minutes." ({items} is the collection's plural item label: images, videos, annotations or sequences), "Compute plot", "Computing plot…", "Running for {m:ss}. The first compute can take several minutes."
- Load the repo skills before editing: `python-guide`, `backend-guide`, `clean-code` for `.py`; `frontend-guide`, `clean-code` for `.ts`/`.svelte`.
- Frontend commands run with Node from `lightly_studio_view/.nvmrc` (24.13.1).

## Review Focus

1. Panel closed and reopened mid-compute: shows the computing state with the original start time, not the prompt. Test in Task 4.
2. Two collections: starting a compute on one does not unlock the other. Test in Task 4.
3. Status request fails: the panel shows the error text and sends no plot request. Test in Task 3 and Task 6.
4. Collection with 0 embeddings: status says `embedding_count: 0`, no prompt. Test in Task 2.
5. Filter or color-by change while the prompt shows: still no plot request. Test in Task 6.

---

### Task 0: Branch and mock cleanup

**Files:**
- Delete: `lightly_studio_view/src/lib/components/PlotPanel/PlotStatusBanner/`
- Delete: `lightly_studio_view/src/lib/components/PlotPanel/PlotComputePrompt/` (the mock; Task 5 rebuilds it)
- Modify: `lightly_studio_view/src/lib/components/PlotPanel/PlotPanel.svelte` (remove the `plotMock` import block and the two `plotMock` branches)
- Delete: `.claude/launch.json` (mock dev server config)

- [ ] **Step 1: Rename the branch to the Linear branch name**

Run: `git branch -m gabriel-stu-102-embedding-plot-ask-before-computing-above`

- [ ] **Step 2: Remove the mock files and the `plotMock` lines**

Run: `git status --short`
Expected: only `.experimental/` files untracked; `PlotPanel.svelte` matches `main` (`git diff main -- lightly_studio_view/src/lib/components/PlotPanel/PlotPanel.svelte` is empty).

- [ ] **Step 3: Commit the spec and plan**

```bash
git add .experimental/superpowers/specs/2026-11-16-embedding-plot-compute-prompt-design.md .experimental/superpowers/plans/2026-11-16-embedding-plot-compute-prompt.md
git commit -m "docs: add STU-102 embedding plot compute prompt spec and plan"
```

---

### Task 1: `embedding_plot_resolver.is_computed`

**Files:**
- Modify: `lightly_studio/src/lightly_studio/resolvers/embedding_plot_resolver.py`
- Test: `lightly_studio/tests/resolvers/test_embedding_plot_resolver.py`

**Interfaces:**
- Produces: `embedding_plot_resolver.is_computed(session: Session, collection_id: UUID, embedding_model_id: UUID) -> bool`

- [ ] **Step 1: Write the failing tests**

```python
def test_is_computed__missing_row(db_session: Session) -> None:
    # collection + embedding model, no embedding_plot row
    assert embedding_plot_resolver.is_computed(session=..., collection_id=..., embedding_model_id=...) is False

def test_is_computed__clean_row(db_session: Session) -> None:
    # EmbeddingPlotTable(..., is_dirty=False, data=encode(...))
    assert ... is True

def test_is_computed__dirty_after_embedding_write(db_session: Session) -> None:
    # clean row, then sample_embedding_resolver.create_many(...) for a new sample in the
    # collection (mark_dirty runs), commit
    assert ... is False
```

Also cover the placeholder row (`EmbeddingPlotTable(collection_id=..., embedding_model_id=...)`, defaults: dirty, empty data) → `False`. Use the helpers from `tests.helpers_resolvers` as the existing tests in this file do.

- [ ] **Step 2: Run to verify they fail**

Run: `cd lightly_studio && uv run pytest tests/resolvers/test_embedding_plot_resolver.py -k is_computed -v`
Expected: FAIL with `AttributeError: ... has no attribute 'is_computed'`

- [ ] **Step 3: Implement `is_computed` in `embedding_plot_resolver.py`**

Select only `EmbeddingPlotTable.is_dirty` filtered by both key columns; return `False` when no row, else `not is_dirty`.

- [ ] **Step 4: Run to verify they pass**

Run: `cd lightly_studio && uv run pytest tests/resolvers/test_embedding_plot_resolver.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add lightly_studio/src/lightly_studio/resolvers/embedding_plot_resolver.py lightly_studio/tests/resolvers/test_embedding_plot_resolver.py
git commit -m "feat: add embedding plot is_computed resolver"
```

---

### Task 2: Status route

**Files:**
- Modify: `lightly_studio/src/lightly_studio/api/routes/api/embeddings2d.py`
- Test: `lightly_studio/tests/api/routes/api/test_embeddings2d__status.py`

**Interfaces:**
- Consumes: `embedding_plot_resolver.is_computed` (Task 1), `sample_embedding_resolver.get_embedding_count(session, collection_id, embedding_model_id) -> int` (exists), `collection_embedding_model_resolver.get_default_by_collection_id` (exists)
- Produces: `GET /api/collections/{collection_id}/embeddings2d/status` → `Embeddings2DStatus { is_computed: bool, embedding_count: int }`; route function `get_2d_embeddings_status`, so the generated client exposes `get2dEmbeddingsStatusOptions` and type `Embeddings2DStatus`.

- [ ] **Step 1: Write the failing tests**

```python
def test_get_embeddings2d_status__computed(test_client, db_session) -> None:
    # 3 samples with embeddings, clean plot row
    assert response.json() == {"is_computed": True, "embedding_count": 3}

def test_get_embeddings2d_status__not_computed(test_client, db_session) -> None:
    # 3 samples with embeddings, no plot row
    assert response.json() == {"is_computed": False, "embedding_count": 3}

def test_get_embeddings2d_status__no_embeddings(test_client, db_session) -> None:
    assert response.json() == {"is_computed": False, "embedding_count": 0}

def test_get_embeddings2d_status__unknown_collection(test_client) -> None:
    assert response.status_code == 404
```

Add one test that mocks `twodim_embedding_resolver.get_plot` with `side_effect=AssertionError` and calls the status route on an uncomputed collection: the route must not compute.

- [ ] **Step 2: Run to verify they fail**

Run: `cd lightly_studio && uv run pytest tests/api/routes/api/test_embeddings2d__status.py -v`
Expected: FAIL with 404/405 on the status path

- [ ] **Step 3: Implement `Embeddings2DStatus` and `get_2d_embeddings_status` in `embeddings2d.py`**

Raise `NotFoundError` for an unknown collection (404, per `backend-guide`; do not copy the plot route's legacy `HTTPException`). Reuse the plot route's default-embedding-model lookup.

- [ ] **Step 4: Run to verify they pass, then static checks**

Run: `cd lightly_studio && uv run pytest tests/api/routes/api/test_embeddings2d__status.py tests/api/routes/api/test_embeddings2d.py -v && make static-checks`
Expected: PASS, no lint or type errors

- [ ] **Step 5: Regenerate the API client**

Run: `cd lightly_studio && make export-schema && make mock-webapp-dist && cd ../lightly_studio_view && npm run generate-api-client`
Expected: `grep -n get2dEmbeddingsStatusOptions src/lib/api/lightly_studio_local/@tanstack/svelte-query.gen.ts` finds it. The client is gitignored; nothing to commit from it.

- [ ] **Step 6: Commit**

```bash
git add lightly_studio/src/lightly_studio/api/routes/api/embeddings2d.py lightly_studio/tests/api/routes/api/test_embeddings2d__status.py
git commit -m "feat: add embedding plot status route"
```

---

### Task 3: Pure gate and elapsed formatter

**Files:**
- Create: `lightly_studio_view/src/lib/components/PlotPanel/plotComputeGate/plotComputeGate.ts`
- Test: `lightly_studio_view/src/lib/components/PlotPanel/plotComputeGate/plotComputeGate.test.ts`

**Interfaces:**
- Produces:
  - `PLOT_COMPUTE_CONFIRM_THRESHOLD = 250_000`
  - `type PlotComputeView = 'checking' | 'error' | 'prompt' | 'computing' | 'plot'`
  - `getPlotComputeView(input: { status: { is_computed: boolean; embedding_count: number } | undefined; isStatusError: boolean; isAxesLayout: boolean; isComputeStarted: boolean }): PlotComputeView`
  - `isPlotRequestEnabled(view: PlotComputeView): boolean` → true only for `'computing'` and `'plot'`
  - `formatElapsed(ms: number): string` → `m:ss`, minutes unbounded

- [ ] **Step 1: Write the failing tests**

```ts
it.each([
  [{ isAxesLayout: true, status: undefined }, 'plot'],
  [{ status: undefined }, 'checking'],
  [{ status: undefined, isStatusError: true }, 'error'],
  [{ status: { is_computed: true, embedding_count: 2_000_000 } }, 'plot'],
  [{ status: { is_computed: false, embedding_count: 250_000 } }, 'prompt'],
  [{ status: { is_computed: false, embedding_count: 249_999 } }, 'computing'],
  [{ status: { is_computed: false, embedding_count: 2_000_000 }, isComputeStarted: true }, 'computing'],
  [{ status: { is_computed: false, embedding_count: 0 } }, 'computing']
])('getPlotComputeView(%o) is %s', ...);

expect(isPlotRequestEnabled('prompt')).toBe(false); // also 'checking', 'error'
expect(isPlotRequestEnabled('computing')).toBe(true); // also 'plot'
expect(formatElapsed(0)).toBe('0:00');
expect(formatElapsed(222_000)).toBe('3:42');
expect(formatElapsed(3_725_000)).toBe('62:05');
```

Defaults for omitted fields: `isStatusError: false`, `isAxesLayout: false`, `isComputeStarted: false`.

- [ ] **Step 2: Run to verify they fail**

Run: `cd lightly_studio_view && npx vitest run src/lib/components/PlotPanel/plotComputeGate`
Expected: FAIL, module not found

- [ ] **Step 3: Implement the three exports in `plotComputeGate.ts`**

Order of checks in `getPlotComputeView`: axes layout, status error, status missing, computed, threshold without start, else computing.

- [ ] **Step 4: Run to verify they pass**

Run: `cd lightly_studio_view && npx vitest run src/lib/components/PlotPanel/plotComputeGate`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add lightly_studio_view/src/lib/components/PlotPanel/plotComputeGate
git commit -m "feat: add embedding plot compute gate"
```

---

### Task 4: Status hook, compute-start store, gate hook

**Files:**
- Create: `lightly_studio_view/src/lib/hooks/useEmbeddingPlotStatus/useEmbeddingPlotStatus.ts` (export it from `src/lib/hooks/index.ts` and import it from `$lib/hooks`)
- Modify: `lightly_studio_view/src/lib/hooks/useEmbeddings/useEmbeddings.ts`
- Create: `lightly_studio_view/src/lib/components/PlotPanel/usePlotComputeGate/usePlotComputeGate.svelte.ts`
- Test: `lightly_studio_view/src/lib/components/PlotPanel/usePlotComputeGate/usePlotComputeGate.test.ts`

**Interfaces:**
- Consumes: `get2dEmbeddingsStatusOptions` (Task 2), `getPlotComputeView`, `isPlotRequestEnabled` (Task 3)
- Produces:
  - `useEmbeddingPlotStatus(getCollectionId: () => string)` → TanStack query of `Embeddings2DStatus`
  - `useEmbeddings(collectionId, filters, colorBy = null, axes = null, enabled = true)`; spreads `enabled` into the query options
  - `usePlotComputeGate(params: { getCollectionId: () => string; getIsAxesLayout: () => boolean; getPlotUpdatedAt: () => number })` returning `{ readonly view: PlotComputeView; readonly isPlotRequestEnabled: boolean; readonly embeddingCount: number; readonly startedAt: number | null; readonly statusError: string | null; startCompute(): void }`

Start times live in a module-level `writable<Record<string, number>>` keyed by collection id, so they survive the panel unmounting. `startCompute()` sets `Date.now()` only if the key is absent. When `view === 'computing'` and no start exists (below the threshold), the gate calls `startCompute()` itself. Each time `getPlotUpdatedAt()` changes (a plot load finished, not cached data) in the PaCMAP layout while the status does not say computed, the gate refetches the status once; a text axes load is a projection and does not count. It deletes the start once a fresh status says computed, or once the status refresh after a PaCMAP load that finished after the start completes, even if that status says dirty: a kept start would skip the prompt next time. With a start but no status at hand (the status cache expired), the view is computing. Only a status fetched after mount decides, except while this tab has a start for the collection, because the server can take long to answer during a compute. A failed plot request keeps the start; clearing it is left for a follow-up.

- [ ] **Step 1: Write the failing tests** (mock `useEmbeddingPlotStatus`)

```ts
it('shows the prompt above the threshold and computing after startCompute', ...);
// status { is_computed: false, embedding_count: 300_000 } -> view 'prompt', isPlotRequestEnabled false
// startCompute() -> view 'computing', startedAt is a number

it('keeps the start time when the panel remounts', ...);
// startCompute(), unmount, mount again for the same collection -> view 'computing', same startedAt

it('does not share a started compute across collections', ...);
// startCompute() on 'a' -> a gate for 'b' with 300_000 is still 'prompt'

it('refetches status and clears the start once the plot loads', ...);
// getIsPlotLoaded() true -> refetch called once, startedAt null
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd lightly_studio_view && npx vitest run src/lib/components/PlotPanel/usePlotComputeGate`
Expected: FAIL, module not found

- [ ] **Step 3: Implement `useEmbeddingPlotStatus`, the `enabled` parameter, and `usePlotComputeGate`**

- [ ] **Step 4: Run to verify they pass**

Run: `cd lightly_studio_view && npx vitest run src/lib/components/PlotPanel/usePlotComputeGate src/lib/hooks`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add lightly_studio_view/src/lib/hooks/index.ts lightly_studio_view/src/lib/hooks/useEmbeddingPlotStatus lightly_studio_view/src/lib/hooks/useEmbeddings lightly_studio_view/src/lib/components/PlotPanel/usePlotComputeGate
git commit -m "feat: gate the embedding plot request on plot status"
```

---

### Task 5: `PlotComputePrompt` component

**Files:**
- Create: `lightly_studio_view/src/lib/components/PlotPanel/PlotComputePrompt/PlotComputePrompt.svelte`
- Test: `lightly_studio_view/src/lib/components/PlotPanel/PlotComputePrompt/PlotComputePrompt.test.ts`

**Interfaces:**
- Consumes: `formatElapsed` (Task 3)
- Produces: props `{ view: 'prompt' | 'computing'; embeddingCount: number; startedAt: number | null; onCompute: () => void }`

Layout as in the mock (`.experimental/stu-102-mock/centered-then-banner/1-not-computed-panel.png`, `2-computing-panel.png`): centered column, Lucide `ChartScatter` for the prompt and spinning `LoaderCircle` for computing, Shadcn `Button` for "Compute plot". The count uses `toLocaleString('en-US')`. The timer re-renders every second while mounted. No text-axes link.

- [ ] **Step 1: Write the failing tests**

```ts
it('renders the prompt and calls onCompute', ...);
// view 'prompt', embeddingCount 2_000_000 -> text "Plot not computed",
// "2,000,000 images. The first compute can take several minutes."; click "Compute plot" -> onCompute called once

it('renders the computing state with the elapsed time', ...);
// fake timers; startedAt = now - 222_000 -> "Computing plot…",
// "Running for 3:42. The first compute can take several minutes."; advance 1s -> "3:43"

it('never mentions text axes', ...);
// both views: queryByText(/text axes/i) is null
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd lightly_studio_view && npx vitest run src/lib/components/PlotPanel/PlotComputePrompt`
Expected: FAIL, component not found

- [ ] **Step 3: Implement `PlotComputePrompt.svelte`**

- [ ] **Step 4: Run to verify they pass**

Run: `cd lightly_studio_view && npx vitest run src/lib/components/PlotPanel/PlotComputePrompt`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add lightly_studio_view/src/lib/components/PlotPanel/PlotComputePrompt
git commit -m "feat: add embedding plot compute prompt"
```

---

### Task 6: Wire the gate into `PlotPanel`

**Files:**
- Modify: `lightly_studio_view/src/lib/components/PlotPanel/PlotPanel.svelte` (the `useEmbeddings` call near line 170, `errorText` near line 512, the state block near line 548)
- Test: `lightly_studio_view/src/lib/components/PlotPanel/PlotPanel.test.ts`

**Interfaces:**
- Consumes: `usePlotComputeGate` (Task 4), `PlotComputePrompt` (Task 5), `useEmbeddings(..., enabled)` (Task 4)

Gate params: `getIsAxesLayout: () => $plotAxes !== null`, `getPlotUpdatedAt: () => embeddingsData.dataUpdatedAt` (cached data must not count as a finished compute). Pass `gate.isPlotRequestEnabled` as `useEmbeddings`'s `enabled`. `errorText` also returns `gate.statusError` when `gate.view === 'error'`. The state block gets two branches before `embeddingsData.isLoading`: `gate.view === 'prompt'` renders the prompt; `gate.view === 'computing' && embeddingsData.isFetching` renders the computing state (`isLoading` is false when the key holds an outdated cached plot). `'checking'` renders today's loading text. Everything else is unchanged.

- [ ] **Step 1: Write the failing tests** (mock `usePlotComputeGate` next to the existing `useEmbeddings` mock; default view `'plot'` so existing tests keep passing)

```ts
it('shows the prompt and sends no plot request', ...);
// view 'prompt' -> "Compute plot" visible; useEmbeddings last called with enabled false

it('keeps the request off when the filter changes under the prompt', ...);
// view 'prompt', change the image filter store -> useEmbeddings still called with enabled false

it('shows the computing state while the first compute runs', ...);
// view 'computing', useEmbeddings isLoading true -> "Computing plot…"

it('keeps the normal loading state for a computed plot', ...);
// view 'plot', isLoading true -> "Loading embeddings data..." and no "Computing plot…"

it('shows the status error', ...);
// view 'error', statusError 'boom' -> "Error loading embeddings: boom"
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd lightly_studio_view && npx vitest run src/lib/components/PlotPanel/PlotPanel.test.ts`
Expected: the five new tests FAIL, existing ones PASS

- [ ] **Step 3: Implement the wiring in `PlotPanel.svelte`**

- [ ] **Step 4: Run the panel tests and the full frontend checks**

Run: `cd lightly_studio_view && npx vitest run src/lib/components/PlotPanel && make static-checks`
Expected: PASS, no errors

- [ ] **Step 5: Commit**

```bash
git add lightly_studio_view/src/lib/components/PlotPanel/PlotPanel.svelte lightly_studio_view/src/lib/components/PlotPanel/PlotPanel.test.ts
git commit -m "feat: ask before computing large embedding plots"
```

---

### Task 7: Check it in the running app

- [ ] **Step 1:** Serve a collection with a dev backend, temporarily set `PLOT_COMPUTE_CONFIRM_THRESHOLD` to `1_000` locally (do not commit), open the Embed panel.
Expected: prompt with the image count; Compute starts the computing state with a ticking timer; the plot appears; reopening the panel shows the plot with the normal loading state.
- [ ] **Step 2:** Restore the threshold and confirm `git diff` shows no change to `plotComputeGate.ts`.
