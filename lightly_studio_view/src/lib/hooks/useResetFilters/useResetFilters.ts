import { get } from 'svelte/store';
import type { GridType } from '$lib/types';
import { useAnnotationCollectionsFilter } from '$lib/hooks/useAnnotationCollectionsFilter/useAnnotationCollectionsFilter';
import { useAnnotationTypeFilter } from '$lib/hooks/useAnnotationTypeFilter/useAnnotationTypeFilter';
import { useDimensions } from '$lib/hooks/useDimensions/useDimensions';
import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
import { useMetadataFilters } from '$lib/hooks/useMetadataFilters/useMetadataFilters';
import { useSelectedAnnotationsFilter } from '$lib/hooks/useAnnotationsFilter/useAnnotationsFilter';
import { useTags } from '$lib/hooks/useTags/useTags';

interface UseResetFiltersParams {
    collectionId: string;
    gridType: GridType;
    /** Every annotation source of the current collection, restored as the reset state. */
    annotationSourceIds: string[];
}

interface UseResetFiltersReturn {
    /** Clears every sidebar filter and returns the grid to the unfiltered collection. */
    resetFilters: () => void;
}

/**
 * Clears the filter state the sidebar exposes, in one action.
 *
 * Annotation sources reset to *all selected* rather than none: an empty source selection hides
 * every annotation, which is a filtered state, not a cleared one.
 */
export function useResetFilters({
    collectionId,
    gridType,
    annotationSourceIds
}: UseResetFiltersParams): UseResetFiltersReturn {
    const { clearSelectedAnnotationFilterIds } = useSelectedAnnotationsFilter();
    const { clearAnnotationTypes } = useAnnotationTypeFilter();
    const { clearTagsSelected } = useTags({
        collection_id: collectionId,
        kind: [gridType === 'annotations' ? 'annotation' : 'sample']
    });
    const { updateMetadataValues, updateCategoricalMetadataValues } =
        useMetadataFilters(collectionId);
    const { dimensionsBounds, updateDimensionsValues } = useDimensions();
    const { updateQueryExpr, updateConfusionCell, updateEmbeddingRegion, updateSampleIds } =
        useImageFilters();
    const { setSelectedCollectionIds } = useAnnotationCollectionsFilter();

    const resetFilters = () => {
        clearSelectedAnnotationFilterIds();
        clearAnnotationTypes();
        clearTagsSelected();
        updateMetadataValues({});
        updateCategoricalMetadataValues({});

        const bounds = get(dimensionsBounds);
        if (bounds) {
            updateDimensionsValues(bounds);
        }

        updateQueryExpr(undefined);
        updateConfusionCell(null);
        updateEmbeddingRegion(null);
        updateSampleIds([]);
        setSelectedCollectionIds(annotationSourceIds);
    };

    return { resetFilters };
}
