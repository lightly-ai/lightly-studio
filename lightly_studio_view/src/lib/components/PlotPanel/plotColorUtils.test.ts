import { describe, expect, it } from 'vitest';
import { CATEGORICAL_PALETTE, getColorByLabel } from '$lib/utils';
import {
    FILTERED_COLOR,
    getCategoryColors,
    getCategoryCount,
    getGradientColor,
    getLegendEntries,
    HIDDEN_COLOR,
    NOT_FILTERED_COLOR,
    OTHER_COLOR,
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
            { cat: 3, label: 'Train', color: CATEGORICAL_PALETTE[0], hidden: false },
            { cat: 4, label: 'Validation', color: CATEGORICAL_PALETTE[1], hidden: false }
        ]);
    });

    it('gives 20 discrete categories distinct colors and the Other bucket a neutral one', () => {
        const legend = new Map<number, string>(
            Array.from({ length: 20 }, (_, i) => [i + 3, `value_${i}`] as [number, string])
        );
        legend.set(22, 'Other (a, b)');

        const colors = getCategoryColors(legend, false, true).slice(3);
        expect(new Set(colors.slice(0, 19)).size).toBe(19);
        expect(colors[19]).toBe(OTHER_COLOR);
    });

    it('colors the categories of a numeric field along the gradient', () => {
        const legend = new Map([
            [3, '0'],
            [4, '12'],
            [5, '23']
        ]);
        const gradient = {
            min: 0,
            max: 23,
            positions: new Map([
                [3, 0],
                [4, 0.5],
                [5, 1]
            ])
        };

        expect(getCategoryColors(legend, false, true, gradient)).toEqual([
            HIDDEN_COLOR,
            NOT_FILTERED_COLOR,
            UNASSIGNED_COLOR,
            'rgb(70, 102, 236)',
            'rgb(150, 250, 80)',
            'rgb(197, 42, 11)'
        ]);
        expect(getGradientColor(0.25)).toBe('rgb(39, 215, 195)');
        // Halfway between the blue and cyan stops.
        expect(getGradientColor(0.125)).toBe('rgb(55, 159, 216)');
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
});
