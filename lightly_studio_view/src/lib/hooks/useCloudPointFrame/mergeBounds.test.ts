import { describe, expect, it } from 'vitest';
import { mergeBounds } from './mergeBounds';

describe('mergeBounds', () => {
    it.each([
        { name: 'the array is empty', input: [] },
        { name: 'every bound is null', input: [null, null] }
    ])('returns null when $name', ({ input }) => {
        expect(mergeBounds(input)).toBeNull();
    });

    it('returns the single bound when only one is available', () => {
        expect(mergeBounds([{ min: [1, 2, 3], max: [4, 5, 6] }])).toEqual({
            min: [1, 2, 3],
            max: [4, 5, 6]
        });
    });

    it('takes the axis-wise min and max across bounds', () => {
        expect(
            mergeBounds([
                { min: [1, 5, -3], max: [4, 8, 0] },
                { min: [0, 6, -5], max: [2, 10, 9] }
            ])
        ).toEqual({
            min: [0, 5, -5],
            max: [4, 10, 9]
        });
    });

    it('ignores null bounds when merging', () => {
        expect(mergeBounds([null, { min: [1, 2, 3], max: [4, 5, 6] }, null])).toEqual({
            min: [1, 2, 3],
            max: [4, 5, 6]
        });
    });
});
