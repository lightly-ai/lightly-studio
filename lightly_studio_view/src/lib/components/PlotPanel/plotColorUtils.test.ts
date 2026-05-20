import { describe, expect, it } from 'vitest';
import { getColorByLabel } from '$lib/utils';
import {
    FILTERED_COLOR,
    getCategoryColors,
    getCategoryCount,
    getLegendEntries,
    NOT_FILTERED_COLOR
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

        expect(getCategoryColors(colorLegend, new Set(), true)).toEqual([
            NOT_FILTERED_COLOR,
            FILTERED_COLOR,
            getColorByLabel('Train').color,
            getColorByLabel('Validation').color
        ]);
    });

    it('renders hidden categories with the filtered color', () => {
        const colorLegend = new Map([
            [2, 'Train'],
            [3, 'Validation']
        ]);

        expect(getCategoryColors(colorLegend, new Set([3]), true)).toEqual([
            NOT_FILTERED_COLOR,
            FILTERED_COLOR,
            getColorByLabel('Train').color,
            FILTERED_COLOR
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

    it('uses label colors for labeled categories when requested', () => {
        const legend = new Map([
            [0, 'none'],
            [1, 'filtered'],
            [2, 'labelName']
        ]);

        const labelColor = getColorByLabel('labelName').color;
        const defaultColors = getCategoryColors(legend, new Set(), false);
        const labelColors = getCategoryColors(legend, new Set(), true);

        expect(labelColors).toEqual([NOT_FILTERED_COLOR, FILTERED_COLOR, labelColor]);
        expect(defaultColors[2]).not.toBe(labelColor);
    });
});
