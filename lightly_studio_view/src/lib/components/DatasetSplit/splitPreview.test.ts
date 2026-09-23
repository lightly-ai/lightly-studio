import { describe, expect, it } from 'vitest';
import { getSplitCounts, getSplitError } from './splitPreview';

const splits = [
    { tag_name: 'train', relative_size: 8 },
    { tag_name: 'val', relative_size: 1 },
    { tag_name: 'test', relative_size: 1 }
];
const defaultParams = { splits, sampleCount: 11, existingTagNames: [] };

describe('getSplitCounts', () => {
    it.each([
        { sampleCount: 11, weights: [8, 1, 1], expected: [9, 1, 1] },
        { sampleCount: 5, weights: [1, 1], expected: [3, 2] },
        { sampleCount: 5, weights: [1, 2, 3], expected: [1, 2, 2] },
        { sampleCount: 3, weights: [100, 1, 1], expected: [3, 0, 0] },
        {
            sampleCount: 5,
            weights: [Number.MAX_SAFE_INTEGER, Number.MAX_SAFE_INTEGER],
            expected: [3, 2]
        }
    ])(
        'allocates $sampleCount samples with weights $weights',
        ({ sampleCount, weights, expected }) => {
            const rows = weights.map((relative_size, index) => ({
                tag_name: `${index}`,
                relative_size
            }));
            const counts = getSplitCounts(sampleCount, rows);
            expect(counts).toEqual(expected);
            expect(counts.reduce((total, count) => total + count, 0)).toBe(sampleCount);
        }
    );
});

describe('getSplitError', () => {
    it('accepts trimmed, case-sensitive names and zero-count rows', () => {
        expect(
            getSplitError({
                splits: [
                    { tag_name: ' train ', relative_size: 100 },
                    { tag_name: 'Train', relative_size: 1 }
                ],
                sampleCount: 2,
                existingTagNames: ['TRAIN']
            })
        ).toBeUndefined();
    });

    it.each([0, -1, 1.5, NaN, Infinity, Number.MAX_SAFE_INTEGER + 1])(
        'rejects weight %s',
        (relative_size) => {
            expect(
                getSplitError({
                    ...defaultParams,
                    splits: [{ ...splits[0], relative_size }, ...splits.slice(1)]
                })
            ).toContain('Weights must be positive whole numbers');
        }
    );

    it.each([
        { names: [' ', 'val'], existingTagNames: [], error: 'Enter a name' },
        { names: ['train', ' train '], existingTagNames: [], error: 'different name' },
        { names: [' train ', 'val'], existingTagNames: ['train'], error: 'already exists' },
        { names: ['train'], existingTagNames: [], error: 'At least two' },
        { names: [], existingTagNames: [], error: 'At least two' }
    ])('rejects invalid names or row counts: $names', ({ names, existingTagNames, error }) => {
        expect(
            getSplitError({
                ...defaultParams,
                splits: names.map((tag_name) => ({ tag_name, relative_size: 1 })),
                existingTagNames
            })
        ).toContain(error);
    });

    it.each([0, 2])('rejects insufficient scope size %s', (sampleCount) => {
        expect(getSplitError({ ...defaultParams, sampleCount })).toContain('matching samples');
    });
});
