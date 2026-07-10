import { type Readable } from 'svelte/store';
import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
import { useRegionFilterVisibility } from './useRegionFilterVisibility';

export function useEmbeddingFilterForImages(
    collectionId: Readable<string>,
    setRangeSelectionForCollection: (collectionId: string, selection: null) => void
) {
    const { updateEmbeddingRegion } = useImageFilters();

    // The image lasso selection is stored as geometry (embedding_region) and sent to the
    // backend rather than as a resolved sample-id list (see LIG-9903), so the chip count comes
    // from the plot-propagated count and clearing removes the region.
    return useRegionFilterVisibility(
        collectionId,
        () => updateEmbeddingRegion(null),
        setRangeSelectionForCollection
    );
}

export type EmbeddingFilterResult = ReturnType<typeof useEmbeddingFilterForImages>;
