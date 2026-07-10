# Issue 0 — Shared foundation: unified metadata aggregation endpoint + metadata-info extension

**Depends on:** nothing. **Blocks:** Issues 1, 2. **Gates:** Issue 3.

## Goal
Provide the shared backend aggregation that Features 1, 2, and 3 all need, so distinct
categorical values, counts, numeric histograms, and GPS-key presence come from one place
instead of being re-derived per feature.

## Backend

### 1. Unified distribution endpoint
Add `POST /collections/{collection_id}/metadata/{key}/distribution` (in
`api/routes/api/metadata.py`).

- **Request:** optional `filter` (the existing sample/image/video/annotation filter
  union already used elsewhere) + optional `bins` for numeric (default ~25, equal-width).
- **Response (categorical — key type `string`/`boolean`):** `[{value, count}]` via SQL
  `GROUP BY` on the JSON-extracted value. Include an explicit `(none)` entry for samples
  missing the key. (Reuse the JSON-extract approach from `metadata_filter.py` /
  `get_metadata_info._get_metadata_min_max_values`.)
- **Response (numerical — key type `integer`/`float`):** equal-width histogram bins over
  the key's global min/max: `{bin_edges: [...], counts: [...], none_count: N}`.
  Prefer SQL-side bucketing; fetch-and-bin is acceptable at 100k if simpler.
- Respect the optional `filter` so the endpoint can serve per-tag series for Feature 2
  (call once per tag with that tag's filter) and honor active filtering.

### 2. Extend `get_metadata_info`
`resolvers/metadata_resolver/sample/get_metadata_info.py` + `MetadataInfoView`
(`models/metadata.py`):
- Report **categorical** keys' distinct values (or at least mark them
  `type in {string, boolean}`) so the frontend can list them without a hue-wheel hack.
- Report the **`gps_coordinate`** type (currently ignored) so the frontend can detect GPS
  presence and gate the map (Feature 3).

## Frontend
- Regenerate the API client (`sdk.gen.ts` / `types.gen.ts`) for the new endpoint +
  `MetadataInfoView` fields.
- Add a thin hook (e.g. `useMetadataDistribution`) wrapping the generated call, returning
  categorical counts or numeric histogram bins. Reused by Issues 1 and 2.

## Acceptance
- Endpoint returns correct categorical counts (incl. `(none)`) and numeric histograms for
  a filtered and unfiltered request.
- `metadata/info` now exposes categorical keys and `gps_coordinate` keys.

## Notes / scope
- Demo branch: no need for pagination or streaming; JSON is fine at these cardinalities.
- Cardinality is ≤~10, so no top-N truncation required at the endpoint (panel already has
  its own top-N display control).
