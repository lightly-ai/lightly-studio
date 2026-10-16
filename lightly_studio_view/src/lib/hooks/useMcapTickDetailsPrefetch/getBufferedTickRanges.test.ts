import { describe, expect, it } from 'vitest';
import { getBufferedTickRanges } from './getBufferedTickRanges';

describe('getBufferedTickRanges', () => {
    it('merges sorted contiguous indexes', () => {
        expect(getBufferedTickRanges(new Set([5, 2, 3, 8, 9]))).toEqual([
            { startIndex: 2, endIndex: 3 },
            { startIndex: 5, endIndex: 5 },
            { startIndex: 8, endIndex: 9 }
        ]);
    });
});
