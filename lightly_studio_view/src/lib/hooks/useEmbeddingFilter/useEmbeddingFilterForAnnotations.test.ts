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
const regionSelection = { embeddingRegion: region, sampleIds: [] };
const pickSelection = { embeddingRegion: null, sampleIds: ['annotation-1'] };

describe('useAnnotationPlotSelection', () => {
    beforeEach(() => {
        clearAnnotationPlotSelection('coll-1');
    });

    it('stores the plot region and the picks in a shared store', () => {
        const { annotationPlotRegion, annotationPlotPickedSampleIds, savePlotSelection } =
            useAnnotationPlotSelection();
        savePlotSelection(regionSelection);
        expect(get(annotationPlotRegion)).toEqual(region);

        savePlotSelection(pickSelection);
        expect(get(annotationPlotRegion)).toBeNull();
        expect(get(annotationPlotPickedSampleIds)).toEqual(['annotation-1']);
    });

    it('clearAnnotationPlotSelection resets the store', () => {
        const { annotationPlotPickedSampleIds, savePlotSelection } = useAnnotationPlotSelection();
        savePlotSelection(pickSelection);
        clearAnnotationPlotSelection('coll-1');
        expect(get(annotationPlotPickedSampleIds)).toEqual([]);
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

    it.each([
        { name: 'region', selection: regionSelection },
        { name: 'picks', selection: pickSelection }
    ])('clearFilter clears the $name, count and range selection', ({ selection }) => {
        const { savePlotSelection } = useAnnotationPlotSelection();
        savePlotSelection(selection);
        setPlotSelectionCount('coll-1', 3);

        const { clearFilter, effectiveCount } = useEmbeddingFilterForAnnotations(
            collectionId,
            setRangeSelection
        );
        clearFilter();

        const { annotationPlotRegion, annotationPlotPickedSampleIds } =
            useAnnotationPlotSelection();
        expect(get(annotationPlotRegion)).toBeNull();
        expect(get(annotationPlotPickedSampleIds)).toEqual([]);
        expect(get(effectiveCount)).toBe(0);
        expect(setRangeSelection).toHaveBeenCalledWith('coll-1', null);
    });
});
