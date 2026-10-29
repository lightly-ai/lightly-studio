import { describe, expect, it } from 'vitest';
import { getSelectedPointIndices, getSelectedPointRadius } from './selectedPoints';

describe('getSelectedPointIndices', () => {
    it('returns the points at or above the Included category while a selection is active', () => {
        // 0 hidden, 1 excluded, 2 included, 3+ colored.
        const category = new Uint8Array([0, 1, 2, 3, 1, 5]);

        expect(getSelectedPointIndices(category, true)).toEqual([2, 3, 5]);
    });

    it('returns no points without a selection', () => {
        expect(getSelectedPointIndices(new Uint8Array([2, 3]), false)).toEqual([]);
        expect(getSelectedPointIndices(undefined, true)).toEqual([]);
    });
});

describe('getSelectedPointRadius', () => {
    it('grows with the setting', () => {
        const radii = (['small', 'medium', 'large', 'extra_large'] as const).map(
            getSelectedPointRadius
        );

        expect(radii).toEqual([3, 4, 5, 7]);
    });
});
