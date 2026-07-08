import { omit } from 'lodash-es';
import type { ImagesInfiniteParams } from '$lib/hooks/useImagesInfinite/useImagesInfinite';
import type { NormalModeFilters } from '$lib/hooks/useImagesInfinite/types';

// sample_ids, embedding_region and confusion_cell are set externally (plot selection /
// confusion matrix), not from the component's filter controls, so they are excluded from
// the base-params comparison and merged back instead of being overwritten.
export const paramsWithoutExternalFilters = (params: ImagesInfiniteParams) => {
    return {
        ...params,
        filters:
            params.mode === 'normal'
                ? omit(params.filters, ['sample_ids', 'embedding_region', 'confusion_cell'])
                : undefined
    };
};

// Merge the externally-set selection (sample_ids, embedding_region) and confusion cell from
// the previous filter params into the new base params. The selection is always carried
// forward; the confusion cell is only carried when the collection matches, because the cell
// belongs to a specific evaluation run/collection and must be dropped when navigating to a
// different collection to avoid wrongly filtering the new grid.
export const mergeExternalFilters = (
    baseParams: ImagesInfiniteParams,
    currentParams: ImagesInfiniteParams
): ImagesInfiniteParams => {
    let nextParams = baseParams;

    let currentSampleIds: string[] = [];
    let currentEmbeddingRegion: NormalModeFilters['embedding_region'];
    let currentConfusionCell: NormalModeFilters['confusion_cell'];
    if (currentParams.mode === 'normal') {
        currentSampleIds = currentParams.filters?.sample_ids ?? [];
        currentEmbeddingRegion = currentParams.filters?.embedding_region;
        if (currentParams.collection_id === baseParams.collection_id) {
            currentConfusionCell = currentParams.filters?.confusion_cell;
        }
    }

    if (
        nextParams.mode === 'normal' &&
        (currentSampleIds.length > 0 || currentEmbeddingRegion || currentConfusionCell)
    ) {
        nextParams = {
            ...nextParams,
            filters: {
                ...(nextParams.filters ?? {}),
                sample_ids: currentSampleIds.length > 0 ? currentSampleIds : undefined,
                embedding_region: currentEmbeddingRegion,
                confusion_cell: currentConfusionCell
            }
        };
    }

    return nextParams;
};
