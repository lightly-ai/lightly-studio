import { describe, expect, it } from 'vitest';
import { getColorByLabel } from '$lib/utils';
import {
    FILTERED_COLOR,
    getCategoryColors,
    getCategoryCount,
    getLegendEntries,
    HIDDEN_COLOR,
    NOT_FILTERED_COLOR,
    UNASSIGNED_COLOR
} from './plotColorUtils';

describe('plotColorUtils', () => {
    it('returns the reserved count when the legend is empty', () => {
        expect(getCategoryCount(undefined)).toBe(3);
    });

    it('returns the highest legend category plus one', () => {
        const colorLegend = new Map([
            [3, 'Train'],
            [5, 'Validation']
        ]);

        expect(getCategoryCount(colorLegend)).toBe(6);
    });

    it('keeps the reserved categories fixed', () => {
        expect(getCategoryColors(undefined)).toEqual([
            HIDDEN_COLOR,
            NOT_FILTERED_COLOR,
            FILTERED_COLOR
        ]);
    });

    it('uses label-based colors for categories above the reserved slots', () => {
        const colorLegend = new Map([
            [3, 'Train'],
            [4, 'Validation']
        ]);

        expect(getCategoryColors(colorLegend, true, true)).toEqual([
            HIDDEN_COLOR,
            NOT_FILTERED_COLOR,
            UNASSIGNED_COLOR,
            getColorByLabel('Train').color,
            getColorByLabel('Validation').color
        ]);
    });

    it('builds legend entries from categories above the reserved slots', () => {
        expect(
            getLegendEntries(
                // A reserved category (2) is included here to verify it is excluded from the entries.
                new Map([
                    [2, 'should be excluded'],
                    [4, 'Validation'],
                    [3, 'Train']
                ]),
                new Set([4])
            )
        ).toEqual([
            { cat: 3, label: 'Train', color: getColorByLabel('Train').color, hidden: false },
            {
                cat: 4,
                label: 'Validation',
                color: getColorByLabel('Validation').color,
                hidden: true
            }
        ]);
    });

    it('uses discrete legend colors when label colors are disabled', () => {
        expect(
            getLegendEntries(
                new Map([
                    [3, 'Train'],
                    [4, 'Validation']
                ]),
                new Set(),
                false
            )
        ).toEqual([
            { cat: 3, label: 'Train', color: 'rgb(255, 0, 136)', hidden: false },
            { cat: 4, label: 'Validation', color: 'rgb(0, 193, 150)', hidden: false }
        ]);
    });

    it('uses unassigned color for category 2 when colorBy is active', () => {
        const colorLegend = new Map([
            [3, 'Train'],
            [4, 'Validation']
        ]);

        expect(getCategoryColors(colorLegend, false, true)[2]).toBe(UNASSIGNED_COLOR);
        expect(getCategoryColors(colorLegend)[2]).toBe(FILTERED_COLOR);
    });

    it('uses label colors for labeled categories when requested', () => {
        const legend = new Map([[3, 'labelName']]);

        const labelColor = getColorByLabel('labelName').color;
        const defaultColors = getCategoryColors(legend, false);
        const labelColors = getCategoryColors(legend, true, true);

        expect(labelColors).toEqual([
            HIDDEN_COLOR,
            NOT_FILTERED_COLOR,
            UNASSIGNED_COLOR,
            labelColor
        ]);
        expect(defaultColors[3]).not.toBe(labelColor);
    });

    it('colors ordered categories with a monotonic sequential ramp', () => {
        const legend = new Map([
            [3, '0-1'],
            [4, '1-2'],
            [5, '2-3']
        ]);
        const colors = getCategoryColors(legend, false, true, true);

        // Reserved slots are unaffected by the ordered ramp.
        expect(colors[0]).toBe(HIDDEN_COLOR);
        expect(colors[1]).toBe(NOT_FILTERED_COLOR);
        expect(colors[2]).toBe(UNASSIGNED_COLOR);

        // Colored bins darken monotonically from the first (lowest) to the last (highest).
        const brightness = (color: string) =>
            (color.match(/\d+/g) ?? []).map(Number).reduce((sum, channel) => sum + channel, 0);
        expect(brightness(colors[3])).toBeGreaterThan(brightness(colors[4]));
        expect(brightness(colors[4])).toBeGreaterThan(brightness(colors[5]));

        // The ordered ramp differs from the categorical hue wheel used otherwise.
        const hueWheelColors = getCategoryColors(legend, false, true, false);
        expect(colors[3]).not.toBe(hueWheelColors[3]);
    });

    it('colors legend entries with the sequential ramp when ordered', () => {
        const legend = new Map([
            [3, '0-1'],
            [4, '1-2']
        ]);
        const entries = getLegendEntries(legend, new Set(), false, true);
        const rampColors = getCategoryColors(legend, false, false, true);

        expect(entries.map((entry) => entry.color)).toEqual([rampColors[3], rampColors[4]]);
    });
});
