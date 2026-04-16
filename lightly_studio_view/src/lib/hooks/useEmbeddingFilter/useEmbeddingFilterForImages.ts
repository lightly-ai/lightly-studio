import { derived, type Readable } from 'svelte/store';
import { isNormalModeParams } from '$lib/hooks/useImagesInfinite/useImagesInfinite';
import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
import { useFilterVisibility } from './useFilterVisibility';

export function useEmbeddingFilterForImages(
    collectionId: Readable<string>,
    setRangeSelectionForCollection: (collectionId: string, selection: null) => void
) {
    const { filterParams, updateSampleIds } = useImageFilters();

    const activeSampleIds = derived(
        [filterParams, collectionId],
        ([$filterParams, $collectionId]) => {
            if (!$filterParams?.collection_id || $filterParams.collection_id !== $collectionId) {
                return [];
            }
            if (!isNormalModeParams($filterParams)) {
                return [];
            }
            return $filterParams.filters?.sample_ids ?? [];
        }
    );

    return useFilterVisibility(
        collectionId,
        activeSampleIds,
        updateSampleIds,
        setRangeSelectionForCollection
    );
}

export type EmbeddingFilterResult = ReturnType<typeof useEmbeddingFilterForImages>;
