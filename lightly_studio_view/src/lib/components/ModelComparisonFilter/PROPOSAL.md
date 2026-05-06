# Annotation Collection Comparison — Implementation Proposal

Validated by the Storybook prototype at `Prototypes/ModelComparisonFilter`.

---

## Overview

This scope focuses on **filtering only** (which images to show in the grid and how overlays are colored).

Out of scope for now:

- Stats panel
- Backend stats/comparison endpoints and related hooks

The UI should keep the existing Labels menu behavior (including counters), but counters must account for the currently selected annotation collections.

---

## Frontend Components

### New components

#### `AnnotationCollectionsMenu`

Mirrors the existing `LabelsMenu` but for annotation collections.

```typescript
type Props = {
    collections: AnnotationCollectionView[];
    enabledCollectionIds: Set<string>;
    confidenceThresholds: Record<string, number>; // collectionId → 0–1
    onToggleCollection: (collectionId: string) => void;
    onConfidenceChange: (collectionId: string, value: number) => void;
};
```

Renders per collection: checkbox, color swatch, name, and (when enabled) a confidence threshold slider. Color is assigned deterministically from collection id, same as the existing label color algorithm.

---

### Modified components

#### `LabelsMenu`

Keep the existing label counters (`current_count / total_count`) in each label row.

Required adjustment:

- Counter values must be computed from annotations belonging to **enabled/selected collections only** (instead of a single implicit source).
- Label rows should still render correctly when multiple collections are enabled.

No stats-panel replacement is needed in this iteration; label counters remain the only per-label quantitative signal in the sidebar.

Additionally, add `colorByLabel` prop. When true, renders a color swatch next to each label using the label's assigned color. Color switches automatically: label-colors when exactly one collection is enabled, collection-colors otherwise — no manual toggle needed.

```typescript
// add to existing props
colorByLabel: boolean;
labelColors: Record<string, string>; // label_name → hex
```

### New hooks

#### `useAnnotationCollections`

Fetches the list of annotation collections available in the current dataset. Used to populate `AnnotationCollectionsMenu`.

```typescript
function useAnnotationCollections(datasetId: string): {
    collections: Readable<AnnotationCollectionView[]>;
};
```

#### `useAnnotationsFilter` (extend existing)

Add `collectionIds` and `labelNames` to the existing hook and to `AnnotationsFilter`.

Also update the label counter derivation used by `LabelsMenu` so counts are aggregated across selected collections.

---

## Backend Endpoints

### Extend existing

**`POST /collections/{collection_id}/images`**

Extend `AnnotationsFilter` with collection filtering and `label_names`.

```python
class AnnotationsFilter(BaseModel):
    # existing fields ...
    collection_ids: list[str] | None = None
    label_names: list[str] | None = None
```

---

## Data flow

```
User changes filter
    │
    └─► POST /images  (immediate, drives grid pagination and label counters)
```

---

## Proposed tasks

1. Define `AnnotationCollectionsMenu` component API and integrate it into the comparison sidebar.
2. Implement annotation-collection fetching (`useAnnotationCollections`) and wire loading/error states.
3. Extend frontend filter state to include selected `collectionIds` and selected `labelNames`.
4. Update `useAnnotationsFilter` output mapping so it produces `AnnotationsFilter` with `collection_ids` and `label_names`.
5. Keep `LabelsMenu` counters and update counter derivation to aggregate over selected collections only.
6. Add `colorByLabel` and `labelColors` support in `LabelsMenu` and connect color mode switching logic.
7. Extend backend `AnnotationsFilter` schema with `collection_ids` and `label_names`.
8. Update image-list query logic to apply both collection and label-name filters.
9. Add or adjust backend tests for `collection_ids` + `label_names` filtering behavior.
10. Add or adjust frontend tests for `useAnnotationsFilter` mapping (`collectionIds`/`labelNames` -> `AnnotationsFilter`).
11. Add or adjust frontend tests for `LabelsMenu` counters with multiple selected collections.
12. Add or adjust frontend tests for sidebar interactions (collection + label toggles) affecting grid results.
