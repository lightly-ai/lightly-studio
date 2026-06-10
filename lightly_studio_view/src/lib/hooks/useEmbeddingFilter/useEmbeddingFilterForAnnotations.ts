import { writable, type Readable } from 'svelte/store';
import { useFilterVisibility } from './useFilterVisibility';

// LIG-9521 prototype: the embedding plot lasso selection on the annotations route.
// Kept separate from the image/video filter stores so it does not pollute them.
const annotationPlotSampleIds = writable<string[]>([]);

export function useAnnotationPlotSelection() {
    return {
        annotationPlotSampleIds,
        updateSampleIds: (ids: string[]) => annotationPlotSampleIds.set(ids)
    };
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
