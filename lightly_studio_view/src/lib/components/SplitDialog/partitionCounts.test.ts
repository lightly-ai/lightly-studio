import { describe, expect, it } from 'vitest';
import { partitionCounts } from './partitionCounts';

describe('partitionCounts', () => {
    it('splits exactly when shares are whole numbers', () => {
        expect(partitionCounts(1000, { train: 80, val: 10, test: 10 })).toEqual({
            train: 800,
            val: 100,
            test: 100
        });
    });

    it('assigns leftover units by largest remainder', () => {
        // Exact shares 2.8 / 2.8 / 1.4: the two leftover units go to train and val.
        expect(partitionCounts(7, { train: 40, val: 40, test: 20 })).toEqual({
            train: 3,
            val: 3,
            test: 1
        });
    });

    it('always sums to the total', () => {
        const counts = partitionCounts(17, { a: 33, b: 33, c: 34 });
        const sum = Object.values(counts).reduce((acc, value) => acc + value, 0);
        expect(sum).toBe(17);
    });

    it('returns zeros for an empty input set', () => {
        expect(partitionCounts(0, { train: 80, val: 20 })).toEqual({ train: 0, val: 0 });
    });
});
