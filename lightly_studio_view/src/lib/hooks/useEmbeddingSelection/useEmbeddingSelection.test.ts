import { describe, it, expect, vi } from 'vitest';
import { get, writable } from 'svelte/store';
import { useEmbeddingSelection } from './useEmbeddingSelection';

describe('useEmbeddingSelection', () => {
    it('hides and restores the active samples selection', () => {
        const collectionId = writable('col-1');
        const isVideos = writable(false);
        const isSamples = writable(true);
        const imageFilterParams = writable({
            collection_id: 'col-1',
            mode: 'normal' as const,
            filters: { sample_ids: ['a', 'b'] }
        });
        const videoFilterParams = writable(null);

        const updateImageSampleIds = vi.fn((sampleIds: string[]) => {
            imageFilterParams.update((params) => ({
                ...params,
                filters: { ...params.filters, sample_ids: sampleIds.length > 0 ? sampleIds : undefined }
            }));
        });
        const updateVideoSampleIds = vi.fn();
        const setRangeSelectionForcollection = vi.fn();
        const setShowPlot = vi.fn();

        const embeddingSelection = useEmbeddingSelection({
            collectionId,
            isVideos,
            isSamples,
            imageFilterParams,
            videoFilterParams,
            updateImageSampleIds,
            updateVideoSampleIds,
            setRangeSelectionForcollection,
            setShowPlot
        });

        embeddingSelection.setEmbeddingSelectionVisibility(false);

        expect(updateImageSampleIds).toHaveBeenCalledWith([]);
        expect(get(embeddingSelection.hiddenEmbeddingSelectionSampleIds)).toEqual(['a', 'b']);
        expect(get(embeddingSelection.activePlotSelectionSampleIds)).toEqual([]);

        embeddingSelection.setEmbeddingSelectionVisibility(true);

        expect(updateImageSampleIds).toHaveBeenLastCalledWith(['a', 'b']);
        expect(get(embeddingSelection.hiddenEmbeddingSelectionSampleIds)).toEqual([]);
        expect(get(embeddingSelection.activePlotSelectionSampleIds)).toEqual(['a', 'b']);
    });

    it('clears plot selection and current range selection', () => {
        const collectionId = writable('col-1');
        const isVideos = writable(false);
        const isSamples = writable(true);
        const imageFilterParams = writable({
            collection_id: 'col-1',
            mode: 'normal' as const,
            filters: { sample_ids: ['a'] }
        });
        const videoFilterParams = writable(null);

        const updateImageSampleIds = vi.fn();
        const updateVideoSampleIds = vi.fn();
        const setRangeSelectionForcollection = vi.fn();
        const setShowPlot = vi.fn();

        const embeddingSelection = useEmbeddingSelection({
            collectionId,
            isVideos,
            isSamples,
            imageFilterParams,
            videoFilterParams,
            updateImageSampleIds,
            updateVideoSampleIds,
            setRangeSelectionForcollection,
            setShowPlot
        });

        embeddingSelection.clearPlotSelection();

        expect(setRangeSelectionForcollection).toHaveBeenCalledWith('col-1', null);
        expect(updateImageSampleIds).toHaveBeenCalledWith([]);
    });
});
