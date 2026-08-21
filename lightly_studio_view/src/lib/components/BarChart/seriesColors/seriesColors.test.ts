import { describe, expect, it } from 'vitest';
import {
    assignSeriesColors,
    colorForSeries,
    extendedSeriesColor,
    SERIES_COLORS
} from './seriesColors';

describe('extendedSeriesColor', () => {
    it('returns the palette color for indices within the first cycle', () => {
        for (let i = 0; i < SERIES_COLORS.length; i++) {
            expect(extendedSeriesColor(i)).toBe(SERIES_COLORS[i]);
        }
    });

    it('generates an opaque color after the base palette', () => {
        const color = extendedSeriesColor(SERIES_COLORS.length);
        expect(color).toMatch(/^hsl\([\d.]+ 60% 55%\)$/);
    });

    it('keeps later-cycle colors valid, opaque, and distinct', () => {
        const colors = [extendedSeriesColor(40), extendedSeriesColor(50)];
        expect(colors).toEqual([
            expect.stringMatching(/^hsl\([\d.]+ 60% 55%\)$/),
            expect.stringMatching(/^hsl\([\d.]+ 60% 55%\)$/)
        ]);
        expect(new Set(colors).size).toBe(2);
    });
});

describe('colorForSeries', () => {
    it('always returns a color from the palette', () => {
        for (const id of ['a', 'tag-1', 'abc', 'hello-world', '']) {
            expect(SERIES_COLORS).toContain(colorForSeries(id));
        }
    });

    it('returns the same color for the same id', () => {
        expect(colorForSeries('stable-id')).toBe(colorForSeries('stable-id'));
    });

    it('returns different colors for different ids (best-effort)', () => {
        const colors = ['id-one', 'id-two', 'id-three'].map(colorForSeries);
        const unique = new Set(colors);
        expect(unique.size).toBeGreaterThan(1);
    });
});

describe('assignSeriesColors', () => {
    it('returns an empty map for an empty list', () => {
        expect(assignSeriesColors([])).toEqual(new Map());
    });

    it('assigns a color to every series id', () => {
        const ids = ['a', 'b', 'c'];
        const result = assignSeriesColors(ids);
        for (const id of ids) {
            expect(result.has(id)).toBe(true);
        }
    });

    it('assigns unique colors to all series', () => {
        const ids = Array.from({ length: SERIES_COLORS.length }, (_, i) => `series-${i}`);
        const result = assignSeriesColors(ids);
        const assigned = [...result.values()];
        expect(new Set(assigned).size).toBe(ids.length);
    });

    it('resolves collisions when two ids hash to the same color', () => {
        // Force a collision by finding two ids that share the same colorForSeries result.
        const groups = new Map<string, string[]>();
        for (let i = 0; i < 100; i++) {
            const id = `id-${i}`;
            const color = colorForSeries(id);
            const list = groups.get(color) ?? [];
            list.push(id);
            groups.set(color, list);
        }
        const colliding = [...groups.values()].find((list) => list.length >= 2);
        if (!colliding) return; // no collision found in range — skip

        const result = assignSeriesColors(colliding.slice(0, 2));
        const [c1, c2] = [...result.values()];
        expect(c1).not.toBe(c2);
    });

    it('produces the same assignment regardless of prior renders', () => {
        const ids = ['x', 'y', 'z'];
        expect(assignSeriesColors(ids)).toEqual(assignSeriesColors(ids));
    });
});
