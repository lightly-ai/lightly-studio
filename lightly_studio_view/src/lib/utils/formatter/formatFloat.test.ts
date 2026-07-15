import { describe, expect, it } from 'vitest';
import { formatFloat, formatFloat2 } from './formatFloat';

describe('formatFloat', () => {
    it('rounds to three fractional digits by default', () => {
        expect(formatFloat(1.23456)).toBe('1.235');
    });

    it('omits fractional digits when the value is whole', () => {
        expect(formatFloat(2)).toBe('2');
    });

    it('respects a custom maximum digit count', () => {
        expect(formatFloat(1.23456, 1)).toBe('1.2');
    });
});

describe('formatFloat2', () => {
    it('formats with two fractional digits', () => {
        expect(formatFloat2(0.876)).toBe('0.88');
    });
});
