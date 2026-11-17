import { get, type Readable } from 'svelte/store';
import { useVideoFilters } from '$lib/hooks/useVideoFilters/useVideoFilters';
import { useRegionFilterVisibility } from './useRegionFilterVisibility';
import { EMPTY_PLOT_SELECTION } from './useEmbeddingPlotSelection';

export function useEmbeddingFilterForVideos(
    collectionId: Readable<string>,
    setRangeSelectionForCollection: (collectionId: string, selection: null) => void
) {
    const { filterParams, updatePlotSelection } = useVideoFilters();

    return useRegionFilterVisibility(
        collectionId,
        () => {
            if (get(filterParams)?.collection_id === get(collectionId)) {
                updatePlotSelection(EMPTY_PLOT_SELECTION);
            }
        },
        setRangeSelectionForCollection
    );
}
