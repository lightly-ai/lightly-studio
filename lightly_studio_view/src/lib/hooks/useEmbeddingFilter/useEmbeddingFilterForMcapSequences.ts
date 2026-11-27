import { get, type Readable } from 'svelte/store';
import { useMcapSequenceFilters } from '$lib/hooks/useMcapSequenceFilters/useMcapSequenceFilters';
import { useRegionFilterVisibility } from './useRegionFilterVisibility';

export function useEmbeddingFilterForMcapSequences(
    collectionId: Readable<string>,
    setRangeSelectionForCollection: (collectionId: string, selection: null) => void
) {
    const { filterParams, updateEmbeddingRegion } = useMcapSequenceFilters();

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
