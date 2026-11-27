import { describe, it, expect, beforeEach, vi } from 'vitest';
import { get, writable } from 'svelte/store';
import { useMcapSequenceFilters } from '$lib/hooks/useMcapSequenceFilters/useMcapSequenceFilters';
import { clearPlotSelectionCount, setPlotSelectionCount } from './useEmbeddingPlotSelection';
import { useEmbeddingFilterForMcapSequences } from './useEmbeddingFilterForMcapSequences';

describe('useEmbeddingFilterForMcapSequences', () => {
    const collectionId = writable('coll-1');
    const setRangeSelection = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
        clearPlotSelectionCount('coll-1');
        collectionId.set('coll-1');

        const { filterParams, setCollectionId } = useMcapSequenceFilters();
        filterParams.set(null);
        setCollectionId('coll-1');
    });

    it('isVisible reflects the propagated selection count', () => {
        setPlotSelectionCount('coll-1', 2);

        const { isVisible, effectiveCount } = useEmbeddingFilterForMcapSequences(
            collectionId,
            setRangeSelection
        );
        expect(get(isVisible)).toBe(true);
        expect(get(effectiveCount)).toBe(2);
    });

    it('clearFilter clears the embedding region when the collection matches', () => {
        const { filterParams, updateEmbeddingRegion } = useMcapSequenceFilters();
        updateEmbeddingRegion({
            polygon: [
                { x: 0, y: 0 },
                { x: 1, y: 0 },
                { x: 1, y: 1 }
            ]
        });
        setPlotSelectionCount('coll-1', 3);

        const { clearFilter, effectiveCount } = useEmbeddingFilterForMcapSequences(
            collectionId,
            setRangeSelection
        );
        clearFilter();

        expect(get(filterParams)?.embedding_region).toBeUndefined();
        expect(get(effectiveCount)).toBe(0);
        expect(setRangeSelection).toHaveBeenCalledWith('coll-1', null);
    });

    it('clearFilter does not touch the embedding region when the collection differs', () => {
        const { filterParams, updateEmbeddingRegion } = useMcapSequenceFilters();
        const region = {
            polygon: [
                { x: 0, y: 0 },
                { x: 1, y: 0 },
                { x: 1, y: 1 }
            ]
        };
        updateEmbeddingRegion(region);
        setPlotSelectionCount('coll-1', 3);

        collectionId.set('coll-2');
        const { clearFilter } = useEmbeddingFilterForMcapSequences(collectionId, setRangeSelection);
        clearFilter();

        expect(get(filterParams)?.embedding_region).toEqual(region);
        expect(setRangeSelection).toHaveBeenCalledWith('coll-2', null);
    });
});
