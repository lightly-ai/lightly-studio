import { beforeEach, describe, expect, it } from 'vitest';
import { get, writable } from 'svelte/store';
import {
    clearPlotSelectionCount,
    getPlotSelectionCount,
    setPlotSelectionCount
} from './useEmbeddingPlotSelection';

describe('useEmbeddingPlotSelection', () => {
    beforeEach(() => {
        clearPlotSelectionCount('coll-1');
        clearPlotSelectionCount('coll-2');
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
});
