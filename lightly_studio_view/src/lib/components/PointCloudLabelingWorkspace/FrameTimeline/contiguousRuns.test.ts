import { describe, expect, it } from 'vitest';
import { toContiguousRuns } from './contiguousRuns';

describe('toContiguousRuns', () => {
    it('returns nothing for an empty track', () => {
        expect(toContiguousRuns([])).toEqual([]);
    });

    it('merges consecutive positions into one run', () => {
        expect(toContiguousRuns([0, 1, 2])).toEqual([{ start: 0, end: 2 }]);
    });

    it('keeps a single frame present between two absent ones as its own run', () => {
        expect(toContiguousRuns([0, 5, 6, 9])).toEqual([
            { start: 0, end: 0 },
            { start: 5, end: 6 },
            { start: 9, end: 9 }
        ]);
    });
});
