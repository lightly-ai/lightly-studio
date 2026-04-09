import { describe, it, expect, vi } from 'vitest';
import { get, writable } from 'svelte/store';
import { useEmbeddingFilter } from './useEmbeddingFilter';
import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
import { useVideoFilters } from '$lib/hooks/useVideoFilters/useVideoFilters';
import { isNormalModeParams } from '$lib/hooks/useImagesInfinite/useImagesInfinite';

function getImageSampleIds() {
    const params = get(useImageFilters().filterParams);
    if (!isNormalModeParams(params)) {
        return undefined;
    }
    return params.filters?.sample_ids;
}

describe('useEmbeddingFilter', () => {
    it('hides and restores the active samples filter', () => {
        const collectionId = writable('col-1');
        const isVideos = writable(false);
        const isSamples = writable(true);
        const setRangeSelectionForcollection = vi.fn();
        const imageFilters = useImageFilters();
        const videoFilters = useVideoFilters();
        imageFilters.updateFilterParams({
            collection_id: 'col-1',
            mode: 'normal',
            filters: { sample_ids: ['a', 'b'] }
        });
        videoFilters.updateFilterParams({
            collection_id: 'col-1',
            filters: {}
        });

        const embeddingFilter = useEmbeddingFilter({
            collectionId,
            isVideos,
            isSamples,
            setRangeSelectionForcollection
        });

        embeddingFilter.setEmbeddingFilterVisibility(false);

        expect(getImageSampleIds()).toBeUndefined();
        expect(get(embeddingFilter.hiddenEmbeddingFilterSampleIds)).toEqual(['a', 'b']);
        expect(get(embeddingFilter.activePlotFilterSampleIds)).toEqual([]);

        embeddingFilter.setEmbeddingFilterVisibility(true);

        expect(getImageSampleIds()).toEqual(['a', 'b']);
        expect(get(embeddingFilter.hiddenEmbeddingFilterSampleIds)).toEqual([]);
        expect(get(embeddingFilter.activePlotFilterSampleIds)).toEqual(['a', 'b']);
    });

    it('clears plot filter and current range selection', () => {
        const collectionId = writable('col-1');
        const isVideos = writable(false);
        const isSamples = writable(true);
        const setRangeSelectionForcollection = vi.fn();
        const imageFilters = useImageFilters();
        const videoFilters = useVideoFilters();
        imageFilters.updateFilterParams({
            collection_id: 'col-1',
            mode: 'normal',
            filters: { sample_ids: ['a'] }
        });
        videoFilters.updateFilterParams({
            collection_id: 'col-1',
            filters: {}
        });

        const embeddingFilter = useEmbeddingFilter({
            collectionId,
            isVideos,
            isSamples,
            setRangeSelectionForcollection
        });

        embeddingFilter.clearPlotFilter();

        expect(setRangeSelectionForcollection).toHaveBeenCalledWith('col-1', null);
        expect(getImageSampleIds()).toBeUndefined();
    });
});
