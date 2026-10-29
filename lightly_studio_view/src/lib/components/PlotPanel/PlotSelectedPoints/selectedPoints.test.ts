import { describe, expect, it } from 'vitest';
import { getSelectedPointIndices, getSelectedPointRadius } from './selectedPoints';

describe('getSelectedPointIndices', () => {
    it('returns the included points when filters or a selection exclude others', () => {
        // 0 hidden, 1 excluded, 2 included, 3+ colored.
        const category = new Uint8Array([0, 1, 2, 3, 1, 5]);

        expect(getSelectedPointIndices(category)).toEqual([2, 3, 5]);
    });

    it('returns no points while every point is included', () => {
        expect(getSelectedPointIndices(new Uint8Array([2, 3]))).toEqual([]);
        expect(getSelectedPointIndices(undefined)).toEqual([]);
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
