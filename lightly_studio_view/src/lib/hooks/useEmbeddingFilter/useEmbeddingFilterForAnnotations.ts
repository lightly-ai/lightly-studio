import { writable, type Readable } from 'svelte/store';
import { useFilterVisibility } from './useFilterVisibility';

// For images and videos the lasso selection already lives inside a
// backend-driven filter store (useImageFilters / useVideoFilters), so the
// "active sample ids" can be derived straight from those filter params.
// Annotations have no such filter store, so we keep the lasso selection in
// this small module-level writable instead. The plot (writer) and the grid
// (reader) share it, which is why it lives at module scope rather than being
// created per-component.
const annotationPlotSampleIds = writable<string[]>([]);

export function useAnnotationPlotSelection() {
    return {
        annotationPlotSampleIds,
        saveSampleIds: (ids: string[]) => annotationPlotSampleIds.set(ids)
    };
}

export function clearAnnotationPlotSelection() {
    annotationPlotSampleIds.set([]);
}

// Adapts the local annotation selection store to the shared useFilterVisibility
// functionality, so the annotations route gets the same show/hide/clear behaviour as
// the image and video embedding filters.
export function useEmbeddingFilterForAnnotations(
    collectionId: Readable<string>,
    setRangeSelectionForCollection: (collectionId: string, selection: null) => void
) {
    const { saveSampleIds } = useAnnotationPlotSelection();
    return useFilterVisibility(
        collectionId,
        annotationPlotSampleIds,
        saveSampleIds,
        setRangeSelectionForCollection
    );
}
