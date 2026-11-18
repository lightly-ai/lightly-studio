import { derived, writable, type Readable } from 'svelte/store';
import { useRegionFilterVisibility } from './useRegionFilterVisibility';
import {
    clearPlotSelectionCount,
    EMPTY_PLOT_SELECTION,
    type PlotSelection
} from './useEmbeddingPlotSelection';

// For images the lasso selection lives inside the image filter store; annotations have no such
// store, so we keep the plot selection here at module scope. The plot (writer) and the grid
// (reader) share it. The selection is sent to the backend as geometry (see LIG-9903), so we
// store the polygon, not the resolved sample ids.
const annotationPlotSelection = writable<PlotSelection>(EMPTY_PLOT_SELECTION);
const annotationPlotRegion = derived(
    annotationPlotSelection,
    (selection) => selection.embeddingRegion
);
const annotationPlotPickedSampleIds = derived(
    annotationPlotSelection,
    (selection) => selection.sampleIds
);

export function useAnnotationPlotSelection() {
    return {
        annotationPlotRegion,
        annotationPlotPickedSampleIds,
        savePlotSelection: (selection: PlotSelection) => annotationPlotSelection.set(selection)
    };
}

function clearAnnotationPlotFilter() {
    annotationPlotSelection.set(EMPTY_PLOT_SELECTION);
}

// Clears the shared annotation plot region and the plot-selection count for `collectionId`.
// The region store is global, but the count is per-collection, so leaving it set would keep the
// Plot Filter chip visible after switching away from and back to the collection.
export function clearAnnotationPlotSelection(collectionId: string) {
    clearAnnotationPlotFilter();
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
        clearAnnotationPlotFilter,
        setRangeSelectionForCollection
    );
}
