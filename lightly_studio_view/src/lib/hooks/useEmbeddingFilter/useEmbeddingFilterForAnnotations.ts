import { writable, type Readable } from 'svelte/store';
import { useFilterVisibility } from './useFilterVisibility';

// The embedding plot lasso selection on the annotations route.
const annotationPlotSampleIds = writable<string[]>([]);

export function useAnnotationPlotSelection() {
    return {
        annotationPlotSampleIds,
        updateSampleIds: (ids: string[]) => annotationPlotSampleIds.set(ids)
    };
}

export function clearAnnotationPlotSelection() {
    annotationPlotSampleIds.set([]);
}

export function useEmbeddingFilterForAnnotations(
    collectionId: Readable<string>,
    setRangeSelectionForCollection: (collectionId: string, selection: null) => void
) {
    const { updateSampleIds } = useAnnotationPlotSelection();
    return useFilterVisibility(
        collectionId,
        annotationPlotSampleIds,
        updateSampleIds,
        setRangeSelectionForCollection
    );
}
