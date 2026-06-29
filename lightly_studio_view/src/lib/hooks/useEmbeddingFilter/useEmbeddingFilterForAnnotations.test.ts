import { describe, it, expect, beforeEach, vi } from 'vitest';
import { get, writable } from 'svelte/store';
import {
    clearAnnotationPlotSelection,
    useAnnotationPlotSelection,
    useEmbeddingFilterForAnnotations
} from './useEmbeddingFilterForAnnotations';

describe('useAnnotationPlotSelection', () => {
    beforeEach(() => {
        clearAnnotationPlotSelection();
    });

    it('stores plot sample IDs in a shared store', () => {
        const { annotationPlotSampleIds, updateSampleIds } = useAnnotationPlotSelection();
        updateSampleIds(['a-1', 'a-2']);
        expect(get(annotationPlotSampleIds)).toEqual(['a-1', 'a-2']);
    });

    it('clearAnnotationPlotSelection resets the store', () => {
        const { annotationPlotSampleIds, updateSampleIds } = useAnnotationPlotSelection();
        updateSampleIds(['a-1']);
        clearAnnotationPlotSelection();
        expect(get(annotationPlotSampleIds)).toEqual([]);
    });
});

describe('useEmbeddingFilterForAnnotations', () => {
    const collectionId = writable('coll-1');
    const setRangeSelection = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
        clearAnnotationPlotSelection();
        collectionId.set('coll-1');
    });

    it('isVisible is true when plot sample IDs are set', () => {
        const { updateSampleIds } = useAnnotationPlotSelection();
        updateSampleIds(['id-1', 'id-2']);

        const { isVisible, effectiveCount } = useEmbeddingFilterForAnnotations(
            collectionId,
            setRangeSelection
        );
        expect(get(isVisible)).toBe(true);
        expect(get(effectiveCount)).toBe(2);
    });

    it('clearFilter clears plot sample IDs and range selection', () => {
        const { updateSampleIds } = useAnnotationPlotSelection();
        updateSampleIds(['id-1']);

        const { clearFilter, effectiveCount } = useEmbeddingFilterForAnnotations(
            collectionId,
            setRangeSelection
        );
        clearFilter();

        expect(get(effectiveCount)).toBe(0);
        expect(setRangeSelection).toHaveBeenCalledWith('coll-1', null);
    });
});
