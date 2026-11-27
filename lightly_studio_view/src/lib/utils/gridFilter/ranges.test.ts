import { describe, expect, it } from 'vitest';
import { dimensionRanges, toRange } from './ranges';

describe('toRange', () => {
    it('returns undefined for a missing range', () => {
        expect(toRange(undefined)).toBeUndefined();
    });

    it('turns null bounds into undefined', () => {
        expect(toRange({ min: null, max: 5 })).toStrictEqual({ min: undefined, max: 5 });
    });

    it('keeps set bounds', () => {
        expect(toRange({ min: 1, max: 2 })).toStrictEqual({ min: 1, max: 2 });
    });
});

describe('dimensionRanges', () => {
    it('returns undefined ranges for null bounds', () => {
        expect(dimensionRanges(null)).toEqual({ width: undefined, height: undefined });
    });

    it('has both keys for null bounds', () => {
        const result = dimensionRanges(null);
        expect('width' in result).toBe(true);
        expect('height' in result).toBe(true);
    });

    it('maps bounds to ranges', () => {
        expect(
            dimensionRanges({ min_width: 10, max_width: 20, min_height: 30, max_height: 40 })
        ).toEqual({ width: { min: 10, max: 20 }, height: { min: 30, max: 40 } });
    });
});
