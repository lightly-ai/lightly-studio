import { describe, expect, it } from 'vitest';
import type { MetadataJointDistributionView } from '$lib/api/lightly_studio_local';
import {
    filtersFromRect,
    formatBucketLabel,
    selectionFromFilters,
    selectJointMetadataKeys
} from './jointSelection';

// month buckets: 0 April, 1 March, 2 Other, 3 Missing. year buckets: 0 2025, 1 2026, 2 2027.
const monthByYear: MetadataJointDistributionView = {
    x_axis: {
        key: 'month',
        type: 'string',
        buckets: [
            { kind: 'value', value: 'April' },
            { kind: 'value', value: 'March' },
            { kind: 'other' },
            { kind: 'missing' }
        ]
    },
    y_axis: {
        key: 'year',
        type: 'integer',
        buckets: [
            { kind: 'range', min: 2025, max: 2025 },
            { kind: 'range', min: 2026, max: 2026 },
            { kind: 'range', min: 2027, max: 2027 }
        ]
    },
    counts: [
        [2, 1, 1, 0],
        [1, 0, 0, 1],
        [0, 1, 0, 0]
    ]
};

const unfiltered = {
    metadataValues: { year: { min: 2025, max: 2027 } },
    categoricalMetadataValues: {},
    metadataBounds: { year: { min: 2025, max: 2027 } }
};

describe('selectJointMetadataKeys', () => {
    it('keeps the categorical and numeric keys', () => {
        expect(
            selectJointMetadataKeys([
                { name: 'month', type: 'string' },
                { name: 'tags', type: 'list' },
                { name: 'year', type: 'integer' },
                { name: 'active', type: 'boolean' },
                { name: 'brightness', type: 'float' }
            ])
        ).toEqual(['month', 'year', 'active', 'brightness']);
    });
});

describe('formatBucketLabel', () => {
    it('labels each bucket kind', () => {
        expect(formatBucketLabel({ kind: 'value', value: 'April' }, 'string')).toBe('April');
        expect(formatBucketLabel({ kind: 'value', value: false }, 'boolean')).toBe('false');
        expect(formatBucketLabel({ kind: 'value', value: '' }, 'string')).toBe('(empty)');
        expect(formatBucketLabel({ kind: 'other' }, 'string')).toBe('Other');
        expect(formatBucketLabel({ kind: 'missing' }, 'string')).toBe('Missing');
        expect(formatBucketLabel({ kind: 'range', min: 2025, max: 2025 }, 'integer')).toBe('2025');
        expect(formatBucketLabel({ kind: 'range', min: 0, max: 2 }, 'integer')).toBe('0–2');
        expect(formatBucketLabel({ kind: 'range', min: 0.25, max: 0.5 }, 'float')).toBe('0.25–0.5');
    });
});

describe('filtersFromRect', () => {
    it('filters to one cell, for example April 2025', () => {
        expect(filtersFromRect(monthByYear, { x0: 0, x1: 0, y0: 0, y1: 0 }, unfiltered)).toEqual({
            metadataValues: { year: { min: 2025, max: 2025 } },
            categoricalMetadataValues: { month: ['April'] }
        });
    });

    it('removes both filters when the current selection is selected again', () => {
        const aprilOf2025 = {
            ...unfiltered,
            metadataValues: { year: { min: 2025, max: 2025 } },
            categoricalMetadataValues: { month: ['April'], weather: ['sunny'] }
        };

        expect(filtersFromRect(monthByYear, { x0: 0, x1: 0, y0: 0, y1: 0 }, aprilOf2025)).toEqual({
            metadataValues: { year: { min: 2025, max: 2027 } },
            categoricalMetadataValues: { weather: ['sunny'] }
        });
    });

    it('removes the filter of an axis that the rectangle spans fully', () => {
        expect(filtersFromRect(monthByYear, { x0: 0, x1: 0, y0: 0, y1: 2 }, unfiltered)).toEqual({
            metadataValues: { year: { min: 2025, max: 2027 } },
            categoricalMetadataValues: { month: ['April'] }
        });
    });

    it('skips the other bucket and maps the missing bucket to null', () => {
        expect(filtersFromRect(monthByYear, { x0: 1, x1: 3, y0: 1, y1: 2 }, unfiltered)).toEqual({
            metadataValues: { year: { min: 2026, max: 2027 } },
            categoricalMetadataValues: { month: ['March', null] }
        });
    });

    it('ignores a rectangle that selects only the other bucket of an axis', () => {
        expect(filtersFromRect(monthByYear, { x0: 2, x1: 2, y0: 0, y1: 0 }, unfiltered)).toBeNull();
    });

    it('filters a float axis to the edges of the selected buckets', () => {
        const brightnessByGroup: MetadataJointDistributionView = {
            x_axis: {
                key: 'brightness',
                type: 'float',
                buckets: [
                    { kind: 'range', min: 0, max: 0.5 },
                    { kind: 'range', min: 0.5, max: 1 }
                ]
            },
            y_axis: { key: 'group', type: 'string', buckets: [{ kind: 'value', value: 'a' }] },
            counts: [[1, 2]]
        };
        const state = {
            metadataValues: { brightness: { min: 0, max: 1 } },
            categoricalMetadataValues: {},
            metadataBounds: { brightness: { min: 0, max: 1 } }
        };

        expect(filtersFromRect(brightnessByGroup, { x0: 1, x1: 1, y0: 0, y1: 0 }, state)).toEqual({
            metadataValues: { brightness: { min: 0.5, max: 1 } },
            categoricalMetadataValues: {}
        });
    });
});

describe('selectionFromFilters', () => {
    it('is null while neither axis key is filtered', () => {
        expect(selectionFromFilters(monthByYear, unfiltered)).toBeNull();
    });

    it('reads the selected buckets from the filters of both axis keys', () => {
        const state = {
            ...unfiltered,
            metadataValues: { year: { min: 2026, max: 2027 } },
            // "May" is not a top value of the axis, so it is in the other bucket.
            categoricalMetadataValues: { month: ['April', 'May'] }
        };

        expect(selectionFromFilters(monthByYear, state)).toEqual({ x: [0, 2], y: [1, 2] });
    });

    it('selects every bucket of an axis without a filter', () => {
        const state = { ...unfiltered, categoricalMetadataValues: { month: [null] } };

        expect(selectionFromFilters(monthByYear, state)).toEqual({ x: [3], y: null });
    });
});
