import { describe, expect, it } from 'vitest';
import { getColorByLabel } from '$lib/utils';
import {
    FILTERED_COLOR,
    getCategoryColors,
    getCategoryCount,
    getLegendEntries,
    getPlotColorMode,
    HIDDEN_COLOR,
    NOT_FILTERED_COLOR,
    UNASSIGNED_COLOR
} from './plotColorUtils';

describe('plotColorUtils', () => {
    it.each([
        { colorByType: 'annotation_label', metadataFieldType: undefined, expected: 'label' },
        { colorByType: 'metadata', metadataFieldType: 'float', expected: 'gradient' },
        { colorByType: 'metadata', metadataFieldType: 'integer', expected: 'gradient' },
        { colorByType: 'metadata', metadataFieldType: 'string', expected: 'discrete' },
        { colorByType: 'metadata', metadataFieldType: undefined, expected: 'discrete' },
        { colorByType: 'tags', metadataFieldType: undefined, expected: 'discrete' },
        { colorByType: null, metadataFieldType: undefined, expected: 'discrete' }
    ] as const)(
        'picks $expected colors for $colorByType with field type $metadataFieldType',
        ({ colorByType, metadataFieldType, expected }) => {
            expect(getPlotColorMode({ colorByType, metadataFieldType })).toBe(expected);
        }
    );

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

        expect(getCategoryColors(colorLegend, 'label', true)).toEqual([
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

    it('uses discrete legend colors in discrete mode', () => {
        expect(
            getLegendEntries(
                new Map([
                    [3, 'Train'],
                    [4, 'Validation']
                ]),
                new Set(),
                'discrete'
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

        expect(getCategoryColors(colorLegend, 'discrete', true)[2]).toBe(UNASSIGNED_COLOR);
        expect(getCategoryColors(colorLegend)[2]).toBe(FILTERED_COLOR);
    });

    it('uses label colors for labeled categories when requested', () => {
        const legend = new Map([[3, 'labelName']]);

        const labelColor = getColorByLabel('labelName').color;
        const defaultColors = getCategoryColors(legend, 'discrete');
        const labelColors = getCategoryColors(legend, 'label', true);

        expect(labelColors).toEqual([
            HIDDEN_COLOR,
            NOT_FILTERED_COLOR,
            UNASSIGNED_COLOR,
            labelColor
        ]);
        expect(defaultColors[3]).not.toBe(labelColor);
    });

    it('colors numeric buckets along a gradient from low to high', () => {
        const colorLegend = new Map([
            [3, '0.0 – 0.2'],
            [4, '0.2 – 0.4'],
            [5, '0.4 – 0.6']
        ]);

        expect(getCategoryColors(colorLegend, 'gradient', true)).toEqual([
            HIDDEN_COLOR,
            NOT_FILTERED_COLOR,
            UNASSIGNED_COLOR,
            // Turbo colormap at 0, 0.5 and 1.
            'rgb(35, 23, 27)',
            'rgb(150, 250, 80)',
            'rgb(144, 13, 0)'
        ]);
    });

    it('uses the same gradient colors in the legend as in the plot', () => {
        const colorLegend = new Map([
            [3, '0 – 1'],
            [4, '1 – 2']
        ]);

        const plotColors = getCategoryColors(colorLegend, 'gradient', true);
        const legendColors = getLegendEntries(colorLegend, new Set(), 'gradient').map(
            (entry) => entry.color
        );

        expect(legendColors).toEqual(plotColors.slice(3));
    });
});
