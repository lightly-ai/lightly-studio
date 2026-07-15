import { describe, it, expect, beforeEach, vi } from 'vitest';
import { get, writable } from 'svelte/store';
import type { EmbeddingRegion } from '$lib/api/lightly_studio_local';
import {
    clearAnnotationPlotSelection,
    useAnnotationPlotSelection,
    useEmbeddingFilterForAnnotations
} from './useEmbeddingFilterForAnnotations';
import {
    clearPlotSelectionCount,
    getPlotSelectionCount,
    setPlotSelectionCount
} from './useEmbeddingPlotSelection';

const region: EmbeddingRegion = {
    polygon: [
        { x: 0, y: 0 },
        { x: 1, y: 0 },
        { x: 1, y: 1 }
    ]
};

describe('useAnnotationPlotSelection', () => {
    beforeEach(() => {
        clearAnnotationPlotSelection('coll-1');
    });

    it('stores the plot region in a shared store', () => {
        const { annotationPlotRegion, saveRegion } = useAnnotationPlotSelection();
        saveRegion(region);
        expect(get(annotationPlotRegion)).toEqual(region);
    });

    it('clearAnnotationPlotSelection resets the store', () => {
        const { annotationPlotRegion, saveRegion } = useAnnotationPlotSelection();
        saveRegion(region);
        clearAnnotationPlotSelection('coll-1');
        expect(get(annotationPlotRegion)).toBeNull();
    });

    it('clearAnnotationPlotSelection also clears the plot-selection count', () => {
        const collectionId = writable('coll-1');
        setPlotSelectionCount('coll-1', 5);

        clearAnnotationPlotSelection('coll-1');

        expect(get(getPlotSelectionCount(collectionId))).toBe(0);
    });
});

describe('useEmbeddingFilterForAnnotations', () => {
    const collectionId = writable('coll-1');
    const setRangeSelection = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
        clearAnnotationPlotSelection('coll-1');
        clearPlotSelectionCount('coll-1');
        collectionId.set('coll-1');
    });

    it('isVisible reflects the propagated selection count', () => {
        setPlotSelectionCount('coll-1', 2);

        const { isVisible, effectiveCount } = useEmbeddingFilterForAnnotations(
            collectionId,
            setRangeSelection
        );
        expect(get(isVisible)).toBe(true);
        expect(get(effectiveCount)).toBe(2);
    });

    it('clearFilter clears the region, count and range selection', () => {
        const { saveRegion } = useAnnotationPlotSelection();
        saveRegion(region);
        setPlotSelectionCount('coll-1', 3);

        const { clearFilter, effectiveCount } = useEmbeddingFilterForAnnotations(
            collectionId,
            setRangeSelection
        );
        clearFilter();

        const { annotationPlotRegion } = useAnnotationPlotSelection();
        expect(get(annotationPlotRegion)).toBeNull();
        expect(get(effectiveCount)).toBe(0);
        expect(setRangeSelection).toHaveBeenCalledWith('coll-1', null);
    });
});
