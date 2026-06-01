import { describe, expect, it } from 'vitest';
import { getColorByLabel } from '$lib/utils';
import {
    FILTERED_COLOR,
    getCategoryColors,
    getCategoryCount,
    getLegendEntries,
    NOT_FILTERED_COLOR,
    UNASSIGNED_COLOR
} from './plotColorUtils';

describe('plotColorUtils', () => {
    it('returns the reserved count when the legend is empty', () => {
        expect(getCategoryCount(undefined)).toBe(2);
    });

    it('returns the highest legend category plus one', () => {
        const colorLegend = new Map([
            [1, 'Filtered'],
            [2, 'Train'],
            [4, 'Validation']
        ]);

        expect(getCategoryCount(colorLegend)).toBe(5);
    });

    it('keeps the reserved categories fixed', () => {
        expect(getCategoryColors(undefined)).toEqual([NOT_FILTERED_COLOR, FILTERED_COLOR]);
    });

    it('uses label-based colors for categories above the reserved slots', () => {
        const colorLegend = new Map([
            [2, 'Train'],
            [3, 'Validation']
        ]);

        expect(getCategoryColors(colorLegend, true, true)).toEqual([
            NOT_FILTERED_COLOR,
            UNASSIGNED_COLOR,
            getColorByLabel('Train').color,
            getColorByLabel('Validation').color
        ]);
    });

    it('builds legend entries from categories above the reserved slots', () => {
        expect(
            getLegendEntries(
                new Map([
                    [1, 'Filtered'],
                    [3, 'Validation'],
                    [2, 'Train']
                ]),
                new Set([3])
            )
        ).toEqual([
            { cat: 2, label: 'Train', color: getColorByLabel('Train').color, hidden: false },
            {
                cat: 3,
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
                    [2, 'Train'],
                    [3, 'Validation']
                ]),
                new Set(),
                false
            )
        ).toEqual([
            { cat: 2, label: 'Train', color: 'hsl(0, 70%, 55%)', hidden: false },
            { cat: 3, label: 'Validation', color: 'hsl(180, 70%, 55%)', hidden: false }
        ]);
    });

    it('uses unassigned color for category 1 when colorBy is active', () => {
        const colorLegend = new Map([
            [2, 'Train'],
            [3, 'Validation']
        ]);

        expect(getCategoryColors(colorLegend, false, true)[1]).toBe(UNASSIGNED_COLOR);
        expect(getCategoryColors(colorLegend)[1]).toBe(FILTERED_COLOR);
    });

    it('uses label colors for labeled categories when requested', () => {
        const legend = new Map([
            [0, 'none'],
            [1, 'filtered'],
            [2, 'labelName']
        ]);

        const labelColor = getColorByLabel('labelName').color;
        const defaultColors = getCategoryColors(legend, false);
        const labelColors = getCategoryColors(legend, true, true);

        expect(labelColors).toEqual([NOT_FILTERED_COLOR, UNASSIGNED_COLOR, labelColor]);
        expect(defaultColors[2]).not.toBe(labelColor);
    });
});
