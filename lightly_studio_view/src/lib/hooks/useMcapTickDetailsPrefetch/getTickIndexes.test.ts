import { describe, expect, it } from 'vitest';
import { getTickIndexes } from './getTickIndexes';

describe('getTickIndexes', () => {
    it('clamps, expands, and deduplicates ranges', () => {
        expect(
            getTickIndexes(
                [
                    { startIndex: -2, endIndex: 1 },
                    { startIndex: 1, endIndex: 4 },
                    { startIndex: 10, endIndex: 12 }
                ],
                5
            )
        ).toEqual([0, 1, 2, 3, 4]);
    });

    it('returns no indexes for an empty tick list', () => {
        expect(getTickIndexes([{ startIndex: 0, endIndex: 2 }], 0)).toEqual([]);
    });
});
