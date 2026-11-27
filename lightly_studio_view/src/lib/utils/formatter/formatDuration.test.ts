import { describe, expect, it } from 'vitest';
import { formatDuration } from './formatDuration';

describe('formatDuration', () => {
    it.each([
        [0, '0:00'],
        [0.999, '0:00'],
        [65, '1:05'],
        [3_725, '62:05'],
        [-3, '0:00']
    ])('formatDuration(%d) is %s', (durationS, expected) => {
        expect(formatDuration(durationS)).toBe(expected);
    });
});
