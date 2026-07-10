# Issue 1 — Categorical-metadata balance sampling strategy

**Depends on:** Issue 0 (for the categorical value list in the target UI). **Blocks:** none.

## Goal
Extend balance sampling (today annotation-only) to balance on **one categorical metadata
key at a time**, supporting the same three target modes as annotation balancing:
`uniform`, `input` (match current distribution), and explicit per-value weights.
Multiple keys are handled by **stacking** several single-key strategies (no joint
balancing).

## Design decision
Add a **new, separate strategy type** rather than overloading the existing `balance`
strategy — keeps the annotation path untouched and avoids XOR-field validation.

## Backend
- **Config model** (`sampling/sampling_config.py`): new
  `MetadataClassBalancingStrategy` with `strategy_name: Literal["metadata_balance"]`,
  `metadata_key: str`, `target_distribution: dict[str,float] | "uniform" | "input"`,
  and `strength` (inherited from `SamplingStrategy`).
- **API union** (`api/routes/api/sampling.py`): add the new model to the discriminated
  `Strategy` union.
- **Resolution** (`sampling/sampling_via_db.py`): new branch in `_add_strategy_to_mundig`
  calling a new `_get_metadata_balancing_data`:
  - Fetch per-sample value for the key via `metadata_resolver` (categorical =
    `string`/`boolean`). Each sample's single value → a **one-hot row** in the
    `(n_samples, n_values)` distribution matrix (contrast: annotations build multi-label
    count rows).
  - Build the target vector for `uniform` / `input` / explicit-dict modes, mirroring
    `_get_class_balancing_data` (incl. an "other"/remaining bucket for unlisted values in
    explicit mode).
  - **Missing values:** samples missing the key contribute **zero** (excluded from this
    strategy's influence), matching annotation balancing.
  - Call `mundig.add_class_balancing(matrix, target, strength)` — mechanism unchanged.

## Frontend (must be fully selectable in the strategy picker)
- **Types/registry** (`hooks/useStrategyBuilder/types.ts`): add
  `metadata_balance` params type, `STRATEGY_OPTIONS` entry, `STRATEGY_DEFAULTS` entry.
- **API mapping** (`hooks/useSubmitCombinationSelection/strategyApiMapping.ts`): map UI
  params → `strategy_name: "metadata_balance"` payload (explicit mode → object; else the
  mode string).
- **Form**: new `MetadataClassBalancingForm` (clone of `ClassBalancingForm`) with a
  **categorical metadata-key picker** instead of the annotation-source picker, + the
  target-distribution mode select + strength + per-value weight table.
- **Options source** (`useSamplingCombinationDialog/useStrategyOptions.svelte.ts`):
  `metadataFieldNames` currently filters to `integer`/`float` — add a **categorical**
  (`string`/`boolean`) key source for this form. Distinct values for the weight table
  come from Issue 0.
- Wire into `StrategyCard.svelte` / `SamplingCombinationDialog.svelte`.

## Acceptance
- New strategy is selectable in the sampling dialog, configurable in all three modes,
  and produces a sampling run that shifts the chosen categorical key toward the target.
- Samples missing the key are not dropped by the run; they just don't influence this
  strategy.
- Stacking two `metadata_balance` strategies (different keys) works.
