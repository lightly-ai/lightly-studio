import { describe, expect, it } from 'vitest';
import { getHiddenCategories, getLegendKey } from './legendKeys';

describe('getLegendKey', () => {
    it('gives the reserved rows and the Other bucket fixed keys', () => {
        expect(getLegendKey(1, undefined)).toBe('reserved:excluded');
        expect(getLegendKey(2, 'x')).toBe('reserved:included');
        expect(getLegendKey(255, 'Other (a, b)')).toBe('other');
    });

    it('keys a class slot by its label', () => {
        expect(getLegendKey(7, 'car')).toBe('label:car');
        expect(getLegendKey(7, '')).toBe('label:');
    });

    it('keys a class in the last slot by its label when the values fit', () => {
        expect(getLegendKey(255, 'zebra')).toBe('label:zebra');
    });

    it('gives a class slot without a label no key', () => {
        expect(getLegendKey(7, undefined)).toBeUndefined();
    });
});

describe('getHiddenCategories', () => {
    it('maps a hidden label to its current slot', () => {
        const legend = new Map([
            [3, 'person'],
            [4, 'car']
        ]);
        expect(getHiddenCategories(new Set(['label:car']), legend)).toEqual(new Set([4]));
    });

    it('follows a label to a new slot', () => {
        const legend = new Map([[9, 'car']]);
        expect(getHiddenCategories(new Set(['label:car']), legend)).toEqual(new Set([9]));
    });

    it('maps a label missing from the legend to no slot', () => {
        const legend = new Map([[3, 'person']]);
        expect(getHiddenCategories(new Set(['label:car']), legend)).toEqual(new Set());
    });

    it('maps the Other bucket whatever its label lists', () => {
        const legend = new Map([[255, 'Other (bus, truck)']]);
        expect(getHiddenCategories(new Set(['other']), legend)).toEqual(new Set([255]));
    });

    it('maps the reserved keys to their slots when the legend lacks them', () => {
        const hiddenKeys = new Set(['reserved:excluded', 'reserved:included']);
        expect(getHiddenCategories(hiddenKeys, new Map())).toEqual(new Set([1, 2]));
    });
});
