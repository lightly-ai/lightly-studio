# Issue 3 — Interactive GPS map (MapLibre) with rectangle-select

**Depends on:** Issue 0 (metadata-info reports `gps_coordinate` → gate the rail button).
**Blocks:** none. **Largest / net-new infrastructure.**

## Goal
A real interactive basemap plotting samples by GPS location, with rectangle-select that
drives the shared active filter, and points colored by selected tags.

## Decisions
- **Real basemap** (not a plain lat/lon scatter). **MapLibre GL JS** + **OpenStreetMap
  raster tiles** (no API key; online demo environment). Machine has internet.
- **Rendering:** MapLibre **native circle layer** (GeoJSON source) — handles 100k points,
  no deck.gl dependency.
- **Selection:** custom **shift+drag rectangle** overlay → compute selected samples by a
  **point-in-bbox test against the raw lat/lon held client-side** (not
  `queryRenderedFeatures`). Rectangle only — no polygon/lasso.
- **Selection effect:** push selected `sampleId`s into the **shared active filter** (same
  as the embedding plot — reuse `updateSampleIds`/filter machinery), so the map is
  consistent with the embedding plot and drives the rest of the UI.
- **Coloring by selected tags:** user picks N tags; a point is colored by its tag using
  the **existing tag color assignment** (colors match the embedding plot).
  - Point in **multiple** selected tags → color by **priority** (tag order in the picker).
  - Point in **none** of the selected tags → **dim gray** (`NOT_FILTERED_COLOR`/
    `UNASSIGNED_COLOR`), kept visible so the full geographic spread shows.
  - (Coloring here is deliberately simpler than the embedding plot's full color-by
    pipeline — tags only.)
- **Placement:** a **new panel/view reached via a new button in the rail**, shown **only
  when a `gps_coordinate` key is present** (detected from the extended `metadata/info`).
- **Missing GPS:** samples without GPS are simply omitted from the map.

## Backend
- New endpoint returning `[{sample_id, lat, lon, tag_ids}]` for samples that have GPS,
  respecting the active filter. (Do **not** overload the embeddings2d Arrow endpoint.)
  JSON is fine at 100k for a demo; revisit only if it's visibly slow.

## Frontend
- Add `maplibre-gl` dependency; init a map with OSM raster tiles.
- New view component (map container + tag color-by picker + legend reusing tag colors).
- GeoJSON circle layer fed from the new endpoint; recolor on tag-selection change.
- Shift+drag rectangle overlay + bbox filter → `updateSampleIds`.
- New rail button, gated on GPS presence.

## Acceptance
- Map renders 100k GPS points over an OSM basemap with pan/zoom.
- Selecting tags recolors points (priority for multi-tag; gray for none).
- Shift+drag rectangle selects the enclosed samples and updates the shared filter, which
  reflects in the rest of the app.
- Rail button only appears when GPS metadata exists.
