# Annotation Collection Comparison — Implementation Proposal

Validated by the Storybook prototype at `Prototypes/ModelComparisonFilter`.

---

## Overview

Two independent concerns:

1. **Filtering** — which images to show in the grid (fast, drives pagination)
2. **Stats** — per-collection aggregations for the visible set (can be slow, loads separately)

Keeping them as separate API calls lets the grid render immediately while stats catch up asynchronously.

---

## Frontend Components

### New components

#### `ModelsMenu`

Mirrors the existing `LabelsMenu` but for annotation collections.

```typescript
type Props = {
    collections: AnnotationCollectionView[];
    enabledCollectionIds: Set<string>;
    confidenceThresholds: Record<string, number>;      // collectionId → 0–1
    onToggleCollection: (collectionId: string) => void;
    onConfidenceChange: (collectionId: string, value: number) => void;
};
```

Renders per collection: checkbox, color swatch, name, and (when enabled) a confidence threshold slider. Color is assigned deterministically from collection id, same as the existing label color algorithm.

---

#### `AnnotationCollectionStatsPanel`

Right sidebar. Receives pre-fetched stats and renders one card per enabled collection.

```typescript
type Props = {
    stats: AnnotationCollectionStatsView[];
    comparisonStats: AnnotationComparisonView[];   // empty when <2 collections enabled
    visibleImageCount: number;
    isLoading: boolean;
};
```

Each card shows:
- Annotation count, coverage %, avg confidence, avg box area
- Per-class breakdown: count + avg confidence + relative bar
- `vs ground_truth` section (precision, recall, avg IoU) — rendered only when a GT collection is enabled and this collection is not GT

---

### Modified components

#### `LabelsMenu`

Remove the `current_count / total_count` counters from each label row. They were the only per-label stats surface in the UI; with the `AnnotationCollectionStatsPanel` covering per-class breakdowns (count, avg confidence, relative bar) there is no need to duplicate this in the filter sidebar. The counters also create visual noise that makes the label list harder to scan.

The `current_count` and `total_count` fields can be dropped from the `Annotation` type passed to the component, and the `formatInteger` import removed.

Additionally, add `colorByLabel` prop. When true, renders a color swatch next to each label using the label's assigned color. Color switches automatically: label-colors when exactly one collection is enabled, collection-colors otherwise — no manual toggle needed.

```typescript
// add to existing props
colorByLabel: boolean;
labelColors: Record<string, string>;  // label_name → hex
```

#### `DimensionFilter` (or `useDimensions` hook)

Replace two single `<input type="range">` sliders with the existing `Slider` component (bits-ui, supports dual handles via `value: [min, max]`).

---

### New hooks

#### `useAnnotationCollections`

Fetches the list of annotation collections available in the current dataset. Used to populate `ModelsMenu`.

```typescript
function useAnnotationCollections(datasetId: string): {
    collections: Readable<AnnotationCollectionView[]>;
};
```

#### `useAnnotationCollectionStats`

Separate query from image fetching. Fires after the filter is stable (debounced ~300 ms). Returns per-collection aggregations for the current filter state.

```typescript
function useAnnotationCollectionStats(params: {
    collectionId: string;
    filter: ImageFilter;
    enabledCollectionIds: string[];
    confidenceThresholds: Record<string, number>;
    gtCollectionId: string | null;
    iouThreshold: number;
}): {
    stats: Readable<AnnotationCollectionStatsView[]>;
    comparisonStats: Readable<AnnotationComparisonView[]>;
    isLoading: Readable<boolean>;
};
```

#### `useAnnotationsFilter` (extend existing)

Add `collectionIds` and per-collection `confidenceThresholds` to the existing hook and to `AnnotationsFilter`.

---

## Backend Endpoints

### Extend existing

**`POST /collections/{collection_id}/images`**

Extend `AnnotationsFilter` with two new fields:

```python
class AnnotationsFilter(BaseModel):
    # existing fields ...
    collection_ids: list[str] | None = None
    min_confidence: float | None = None   # applied per-collection using per-collection thresholds
```

For per-collection confidence thresholds, extend to:

```python
class CollectionConfidenceThreshold(BaseModel):
    collection_id: str
    min_confidence: float

class AnnotationsFilter(BaseModel):
    # existing fields ...
    collection_ids: list[str] | None = None
    confidence_thresholds: list[CollectionConfidenceThreshold] | None = None
```

---

### New: annotation collection stats

**`POST /collections/{collection_id}/annotation-collection-stats`**

Returns per-collection aggregations for the filtered image set. Intentionally separate from the image list endpoint so the grid can render before stats are ready.

Request body: same `ImageFilter` as the images endpoint, plus which collections to aggregate.

```python
class AnnotationCollectionStatsRequest(BaseModel):
    image_filter: ImageFilter
    collection_ids: list[str]
    confidence_thresholds: list[CollectionConfidenceThreshold] = []
```

Response:

```python
class ClassStatView(BaseModel):
    label_name: str
    count: int
    avg_confidence: float

class AnnotationCollectionStatsView(BaseModel):
    collection_id: str
    annotation_count: int
    image_coverage: float          # fraction of filtered images with ≥1 annotation
    avg_confidence: float
    avg_box_area: float            # mean normalised bbox area (w×h, 0–1)
    class_stats: list[ClassStatView]
```

---

### New: precision / recall / IoU comparison

**`POST /collections/{collection_id}/annotation-comparison`**

Computes TP/FP/FN by matching prediction boxes against a ground-truth collection using IoU ≥ threshold and same label. Expensive — called only when a GT collection is explicitly set. Client should show a loading state.

```python
class AnnotationComparisonRequest(BaseModel):
    image_filter: ImageFilter
    prediction_collection_ids: list[str]
    gt_collection_id: str
    iou_threshold: float = 0.5
    confidence_thresholds: list[CollectionConfidenceThreshold] = []

class AnnotationComparisonView(BaseModel):
    collection_id: str
    gt_collection_id: str
    iou_threshold: float
    precision: float
    recall: float
    avg_iou: float                 # mean IoU over matched pairs only
    true_positives: int
    false_positives: int
    false_negatives: int
```

---

## Data flow

```
User changes filter
    │
    ├─► POST /images  (immediate, drives grid pagination)
    │
    └─► POST /annotation-collection-stats  (debounced 300ms, drives stats panel)
            │
            └─► POST /annotation-comparison  (only when GT collection enabled)
```

---

## URL Routing Refactor

### Problem

The current URL structure embeds `collection_type` as a path segment:

```
/datasets/{dataset_id}/{collection_type}/{collection_id}/{view}
```

This produces redundant and confusing URLs where the type and the view repeat the same word:

```
/datasets/c8dd3828/image/c8dd3828/images       ← "image" + "images"
/datasets/c8dd3828/video/abc123/videos         ← "video" + "videos"
```

`collection_type` also leaks an internal data model concept that has no meaning to the user.

### Proposed structure

```
/datasets/{dataset_id}/collections/{collection_id}/{view}
```

Examples:

| Before | After |
|--------|-------|
| `/datasets/c8dd3828/image/c8dd3828/images` | `/datasets/c8dd3828/collections/c8dd3828/images` |
| `/datasets/c8dd3828/image/c8dd3828/images/sample-id` | `/datasets/c8dd3828/collections/c8dd3828/images/sample-id` |
| `/datasets/c8dd3828/video/abc123/videos` | `/datasets/c8dd3828/collections/abc123/videos` |
| `/datasets/c8dd3828/video/abc123/frames` | `/datasets/c8dd3828/collections/abc123/frames` |
| `/datasets/c8dd3828/image/abc123/annotations` | `/datasets/c8dd3828/collections/abc123/annotations` |

The static segment `collections/` keeps the hierarchy unambiguous and leaves room for other dataset-level routes (e.g. `/datasets/{id}/settings`).

### What changes

- **SvelteKit routes** — rename the `[collection_type]` directory to the static segment `collections`
- **`routes.ts`** — remove `collectionType` parameter from all route helpers; callers no longer need to pass it
- **`APP_ROUTES`** — update the `COLLECTION_BASE_ROUTE` constant
- **All call sites** — drop the `collectionType` argument; this is the bulk of the migration

### What does not change

- `collection_id` and all view segments (`/images`, `/videos`, `/frames`, `/annotations`, `/captions`, `/groups`) are identical
- The available views per collection are determined by the collection's media type fetched from the API, not from the URL — no logic change required
- Backend is entirely unaffected

### Future improvement: human-readable slugs

Currently collection identifiers in the URL are UUIDs, making links opaque:

```
/datasets/c8dd3828/collections/f3a91b44/images
```

A follow-up could introduce a slug derived from the collection name:

```
/datasets/c8dd3828/collections/ground-truth-v2/images
```

This requires slugs to be unique per dataset and stable after rename. Can be done as a separate step after the structural refactor above.

---

## Open questions

1. **Color assignment** — should collection colors be user-customisable and persisted (like label colors today), or always auto-assigned?
2. **GT collection designation** — explicit UI toggle ("set as ground truth") or inferred from collection name/type?
3. **Confidence threshold scope** — per-collection (more flexible) vs. global single threshold (simpler UI)?
4. **Stats caching** — stats queries can be expensive on large datasets; should results be cached server-side by filter hash?
