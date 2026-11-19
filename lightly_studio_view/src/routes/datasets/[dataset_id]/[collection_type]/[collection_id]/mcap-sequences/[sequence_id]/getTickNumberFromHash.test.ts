import { describe, expect, it } from 'vitest';
import { getTickNumberFromHash } from './getTickNumberFromHash';

describe('getTickNumberFromHash', () => {
    it.each([
        ['#tick=4', 4],
        ['', 1],
        ['#tick=0', 1],
        ['#tick=-2', 1],
        ['#other=4', 1],
        ['#tick=abc', 1],
        ['#tick=1.5', 1]
    ])('returns %s as tick number %i', (hash, expected) => {
        expect(getTickNumberFromHash(hash)).toBe(expected);
    });
});
