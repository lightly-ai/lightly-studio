import { describe, expect, it } from 'vitest';

import { sortSamplesByEvaluationCount } from './sortSamplesByEvaluationCount';

describe('sortSamplesByEvaluationCount', () => {
    const samples = [{ sample_id: 'a' }, { sample_id: 'b' }, { sample_id: 'c' }];
    const counts = {
        a: { fp: 1, fn: 3, tp: 2 },
        b: { fp: 3, fn: 1, tp: 1 },
        c: { fp: 2, fn: 2, tp: 4 }
    };

    it('keeps the original order when no sort is active', () => {
        expect(sortSamplesByEvaluationCount(samples, counts, null)).toEqual(samples);
    });

    it('sorts descending by the selected count metric', () => {
        expect(
            sortSamplesByEvaluationCount(samples, counts, {
                metric: 'fp',
                direction: 'desc'
            }).map((sample) => sample.sample_id)
        ).toEqual(['b', 'c', 'a']);
    });

    it('sorts ascending by the selected count metric', () => {
        expect(
            sortSamplesByEvaluationCount(samples, counts, {
                metric: 'fn',
                direction: 'asc'
            }).map((sample) => sample.sample_id)
        ).toEqual(['b', 'c', 'a']);
    });

    it('treats missing counts as zero', () => {
        expect(
            sortSamplesByEvaluationCount(
                samples,
                { a: { tp: 2 } },
                {
                    metric: 'tp',
                    direction: 'desc'
                }
            ).map((sample) => sample.sample_id)
        ).toEqual(['a', 'b', 'c']);
    });
});
