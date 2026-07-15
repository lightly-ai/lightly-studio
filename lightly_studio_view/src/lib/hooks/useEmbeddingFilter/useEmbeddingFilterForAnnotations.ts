import { writable, type Readable } from 'svelte/store';
import type { EmbeddingRegion } from '$lib/api/lightly_studio_local';
import { useRegionFilterVisibility } from './useRegionFilterVisibility';
import { clearPlotSelectionCount } from './useEmbeddingPlotSelection';

// For images the lasso selection lives inside the image filter store; annotations have no such
// store, so we keep the plot region here at module scope. The plot (writer) and the grid
// (reader) share it. The selection is sent to the backend as geometry (see LIG-9903), so we
// store the polygon, not the resolved sample ids.
const annotationPlotRegion = writable<EmbeddingRegion | null>(null);

export function useAnnotationPlotSelection() {
    return {
        annotationPlotRegion,
        saveRegion: (region: EmbeddingRegion | null) => annotationPlotRegion.set(region)
    };
}

// Clears the shared annotation plot region and the plot-selection count for `collectionId`.
// The region store is global, but the count is per-collection, so leaving it set would keep the
// Embedding Plot Filter chip visible after switching away from and back to the collection.
export function clearAnnotationPlotSelection(collectionId: string) {
    annotationPlotRegion.set(null);
    clearPlotSelectionCount(collectionId);
}

// Adapts the local annotation region selection to the shared region-based visibility, so the
// annotations route gets the same count/clear behaviour as the image embedding filter.
export function useEmbeddingFilterForAnnotations(
    collectionId: Readable<string>,
    setRangeSelectionForCollection: (collectionId: string, selection: null) => void
) {
    return useRegionFilterVisibility(
        collectionId,
        () => annotationPlotRegion.set(null),
        setRangeSelectionForCollection
    );
}
