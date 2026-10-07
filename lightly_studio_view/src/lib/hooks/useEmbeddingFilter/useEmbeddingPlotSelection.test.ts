import { beforeEach, describe, expect, it } from 'vitest';
import { get, writable } from 'svelte/store';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import {
    clearPlotSelectionForCollection,
    clearPlotSelectionCount,
    getPlotSelectionCount,
    setPlotSelectionCount
} from './useEmbeddingPlotSelection';

describe('useEmbeddingPlotSelection', () => {
    beforeEach(() => {
        clearPlotSelectionCount('coll-1');
        clearPlotSelectionCount('coll-2');
        const storage = useGlobalStorage();
        storage.setRangeSelectionForCollection('coll-1', null);
        storage.setRangeSelectionForCollection('coll-2', null);
    });

    it('defaults to zero for an unknown collection', () => {
        const count = getPlotSelectionCount(writable('coll-1'));
        expect(get(count)).toBe(0);
    });

    it('reflects the count set for a collection', () => {
        setPlotSelectionCount('coll-1', 42);
        const count = getPlotSelectionCount(writable('coll-1'));
        expect(get(count)).toBe(42);
    });

    it('keeps counts isolated per collection', () => {
        setPlotSelectionCount('coll-1', 5);
        expect(get(getPlotSelectionCount(writable('coll-1')))).toBe(5);
        expect(get(getPlotSelectionCount(writable('coll-2')))).toBe(0);
    });

    it('clears the count back to zero', () => {
        setPlotSelectionCount('coll-1', 7);
        clearPlotSelectionCount('coll-1');
        expect(get(getPlotSelectionCount(writable('coll-1')))).toBe(0);
    });

    it('clears the count and live range selection for a collection', () => {
        const storage = useGlobalStorage();
        storage.setRangeSelectionForCollection('coll-1', [{ x: 0, y: 0 }]);
        setPlotSelectionCount('coll-1', 7);

        clearPlotSelectionForCollection('coll-1', storage.setRangeSelectionForCollection);

        expect(get(getPlotSelectionCount(writable('coll-1')))).toBe(0);
        expect(get(storage.getRangeSelection('coll-1'))).toBeNull();
    });
});
