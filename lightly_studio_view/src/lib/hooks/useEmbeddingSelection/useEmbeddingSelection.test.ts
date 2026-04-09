import { describe, it, expect, vi } from 'vitest';
import { get, writable } from 'svelte/store';
import { useEmbeddingSelection } from './useEmbeddingSelection';
import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
import { useVideoFilters } from '$lib/hooks/useVideoFilters/useVideoFilters';

describe('useEmbeddingSelection', () => {
    it('hides and restores the active samples selection', () => {
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

        const embeddingSelection = useEmbeddingSelection({
            collectionId,
            isVideos,
            isSamples,
            setRangeSelectionForcollection
        });

        embeddingSelection.setEmbeddingSelectionVisibility(false);

        expect(get(imageFilters.filterParams).filters?.sample_ids).toBeUndefined();
        expect(get(embeddingSelection.hiddenEmbeddingSelectionSampleIds)).toEqual(['a', 'b']);
        expect(get(embeddingSelection.activePlotSelectionSampleIds)).toEqual([]);

        embeddingSelection.setEmbeddingSelectionVisibility(true);

        expect(get(imageFilters.filterParams).filters?.sample_ids).toEqual(['a', 'b']);
        expect(get(embeddingSelection.hiddenEmbeddingSelectionSampleIds)).toEqual([]);
        expect(get(embeddingSelection.activePlotSelectionSampleIds)).toEqual(['a', 'b']);
    });

    it('clears plot selection and current range selection', () => {
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

        const embeddingSelection = useEmbeddingSelection({
            collectionId,
            isVideos,
            isSamples,
            setRangeSelectionForcollection
        });

        embeddingSelection.clearPlotSelection();

        expect(setRangeSelectionForcollection).toHaveBeenCalledWith('col-1', null);
        expect(get(imageFilters.filterParams).filters?.sample_ids).toBeUndefined();
    });
});
