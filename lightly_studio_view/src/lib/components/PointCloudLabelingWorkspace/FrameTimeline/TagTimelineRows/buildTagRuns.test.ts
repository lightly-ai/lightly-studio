import { describe, expect, it } from 'vitest';
import { buildTagRuns } from './buildTagRuns';

const ticks = [0, 1, 2, 5, 6, 7].map((seq_number) => ({ seq_number, timestamp_ns: null }));

describe('buildTagRuns', () => {
    it('groups consecutive ticks and keeps gaps', () => {
        expect(buildTagRuns(ticks, [0, 1, 6, 7])).toEqual([
            { startIndex: 0, endIndex: 1 },
            { startIndex: 4, endIndex: 5 }
        ]);
    });

    it('treats ticks with sparse seq numbers as adjacent', () => {
        expect(buildTagRuns(ticks, [2, 5])).toEqual([{ startIndex: 2, endIndex: 3 }]);
    });

    it('ignores seq numbers that are not ticks', () => {
        expect(buildTagRuns(ticks, [9])).toEqual([]);
    });

    it('returns no runs without seq numbers', () => {
        expect(buildTagRuns(ticks, [])).toEqual([]);
    });
});
