import { describe, expect, it } from 'vitest';
import { SERIES_COLORS, assignSeriesColors, colorForSeries, extendedSeriesColor } from './seriesColors';

describe('colorForSeries', () => {
    it('returns the same color for the same id across calls', () => {
        expect(colorForSeries('tag-a')).toBe(colorForSeries('tag-a'));
    });

    it('returns different colors for different ids', () => {
        expect(colorForSeries('tag-a')).not.toBe(colorForSeries('tag-b'));
    });

    it('always returns a color from the palette', () => {
        for (const id of ['x', 'foo', 'some-long-id-with-dashes', '']) {
            expect(SERIES_COLORS).toContain(colorForSeries(id));
        }
    });
});

describe('extendedSeriesColor', () => {
    it('returns the base palette color for indices within the first cycle', () => {
        expect(extendedSeriesColor(0)).toBe(SERIES_COLORS[0]);
        expect(extendedSeriesColor(SERIES_COLORS.length - 1)).toBe(
            SERIES_COLORS[SERIES_COLORS.length - 1]
        );
    });

    it('appends an opacity suffix for indices beyond the first cycle', () => {
        const color = extendedSeriesColor(SERIES_COLORS.length);
        expect(color.startsWith(SERIES_COLORS[0])).toBe(true);
        expect(color.length).toBeGreaterThan(SERIES_COLORS[0].length);
    });

    it('produces distinct values for different cycles of the same palette slot', () => {
        const first = extendedSeriesColor(0);
        const second = extendedSeriesColor(SERIES_COLORS.length);
        const third = extendedSeriesColor(SERIES_COLORS.length * 2);
        expect(first).not.toBe(second);
        expect(second).not.toBe(third);
    });
});

describe('assignSeriesColors', () => {
    it('returns a color for every id', () => {
        const ids = ['a', 'b', 'c'];
        const colors = assignSeriesColors(ids);
        for (const id of ids) {
            expect(colors.has(id)).toBe(true);
        }
    });

    it('assigns distinct colors when ids hash to the same slot', () => {
        // 'a' and 'k' are known to collide in colorForSeries.
        expect(colorForSeries('a')).toBe(colorForSeries('k'));
        const colors = assignSeriesColors(['a', 'k']);
        expect(colors.get('a')).not.toBe(colors.get('k'));
    });

    it('handles more ids than palette entries without duplicate colors', () => {
        const ids = Array.from({ length: SERIES_COLORS.length + 3 }, (_, i) => `s${i}`);
        const colors = assignSeriesColors(ids);
        const values = [...colors.values()];
        const unique = new Set(values);
        expect(unique.size).toBe(ids.length);
    });

    it('returns an empty map for an empty input', () => {
        expect(assignSeriesColors([])).toEqual(new Map());
    });
});
