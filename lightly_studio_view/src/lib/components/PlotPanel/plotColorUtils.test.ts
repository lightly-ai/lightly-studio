import { describe, expect, it } from 'vitest';
import {
    FILTERED_COLOR,
    getCategoryColors,
    getCategoryCount,
    NOT_FILTERED_COLOR
} from './plotColorUtils';

describe('plotColorUtils', () => {
    it('returns the reserved count when category data is empty', () => {
        expect(getCategoryCount(undefined)).toBe(2);
        expect(getCategoryCount(null)).toBe(2);
        expect(getCategoryCount(new Map())).toBe(2);
    });

    it('returns max category plus one', () => {
        expect(
            getCategoryCount(
                new Map([
                    [0, 'a'],
                    [1, 'b'],
                    [2, 'c'],
                    [3, 'd']
                ])
            )
        ).toBe(4);
        expect(
            getCategoryCount(
                new Map([
                    [0, 'a'],
                    [1, 'b']
                ])
            )
        ).toBe(2);
    });

    it('keeps the reserved categories fixed', () => {
        const legend = new Map([
            [0, 'none'],
            [1, 'filtered']
        ]);
        expect(getCategoryColors(legend)).toEqual([NOT_FILTERED_COLOR, FILTERED_COLOR]);
    });

    it('uses hsl colors for categories above the reserved slots', () => {
        const legend = new Map([
            [0, ''],
            [1, ''],
            [2, ''],
            [3, '']
        ]);
        expect(getCategoryColors(legend)).toEqual([
            NOT_FILTERED_COLOR,
            FILTERED_COLOR,
            'hsl(0, 70%, 55%)',
            'hsl(180, 70%, 55%)'
        ]);
    });

    it('returns filtered color for hidden categories', () => {
        const legend = new Map([
            [0, ''],
            [1, ''],
            [2, '']
        ]);
        const hiddenCategories = new Set([0, 2]);
        expect(getCategoryColors(legend, hiddenCategories)).toEqual([
            FILTERED_COLOR,
            FILTERED_COLOR,
            FILTERED_COLOR
        ]);
    });
});
