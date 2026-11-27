import { type Readable } from 'svelte/store';
import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
import { useRegionFilterVisibility } from './useRegionFilterVisibility';
import { EMPTY_PLOT_SELECTION } from './useEmbeddingPlotSelection';

export function useEmbeddingFilterForImages(
    collectionId: Readable<string>,
    setRangeSelectionForCollection: (collectionId: string, selection: null) => void
) {
    const { updatePlotSelection } = useImageFilters();

    // The image lasso selection is stored as geometry (embedding_region) and sent to the
    // backend rather than as a resolved sample-id list (see LIG-9903), so the chip count comes
    // from the plot-propagated count and clearing removes the region.
    return useRegionFilterVisibility(
        collectionId,
        () => updatePlotSelection(EMPTY_PLOT_SELECTION),
        setRangeSelectionForCollection
    );
}

export type EmbeddingFilterResult = ReturnType<typeof useEmbeddingFilterForImages>;
