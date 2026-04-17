import { derived, type Readable } from 'svelte/store';
import { useVideoFilters } from '$lib/hooks/useVideoFilters/useVideoFilters';
import { useFilterVisibility } from './useFilterVisibility';

export function useEmbeddingFilterForVideos(
    collectionId: Readable<string>,
    setRangeSelectionForCollection: (collectionId: string, selection: null) => void
) {
    const { filterParams, updateSampleIds } = useVideoFilters();

    const activeSampleIds = derived(
        [filterParams, collectionId],
        ([$filterParams, $collectionId]) => {
            if ($filterParams?.collection_id !== $collectionId) {
                return [];
            }
            return $filterParams?.filters?.sample_ids ?? [];
        }
    );

    return useFilterVisibility(
        collectionId,
        activeSampleIds,
        updateSampleIds,
        setRangeSelectionForCollection
    );
}
