import { get, type Readable } from 'svelte/store';
import { useVideoFilters } from '$lib/hooks/useVideoFilters/useVideoFilters';
import { useRegionFilterVisibility } from './useRegionFilterVisibility';

export function useEmbeddingFilterForVideos(
    collectionId: Readable<string>,
    setRangeSelectionForCollection: (collectionId: string, selection: null) => void
) {
    const { filterParams, updateEmbeddingRegion } = useVideoFilters();

    return useRegionFilterVisibility(
        collectionId,
        () => {
            if (get(filterParams)?.collection_id === get(collectionId)) {
                updateEmbeddingRegion(null);
            }
        },
        setRangeSelectionForCollection
    );
}
