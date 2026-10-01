import { describe, expect, it } from 'vitest';
import { formatMetadataValue } from './formatMetadataValue';

describe('formatMetadataValue', () => {
    it('renders null and undefined as "null"', () => {
        expect(formatMetadataValue(null)).toBe('null');
        expect(formatMetadataValue(undefined)).toBe('null');
    });

    it('returns strings unchanged', () => {
        expect(formatMetadataValue('hello')).toBe('hello');
    });

    it('formats integers with separators and floats with decimals', () => {
        expect(formatMetadataValue(1234)).toBe('1,234');
        expect(formatMetadataValue(1.23456)).toBe('1.235');
    });

    it('formats booleans as words', () => {
        expect(formatMetadataValue(true)).toBe('true');
        expect(formatMetadataValue(false)).toBe('false');
    });

    it('formats short primitive arrays inline', () => {
        expect(formatMetadataValue([1, 2, 3])).toBe('[1, 2, 3]');
        expect(formatMetadataValue([])).toBe('[]');
    });

    it('formats small objects on one line', () => {
        expect(formatMetadataValue({ a: 1, b: 'x' })).toBe('{a: 1, b: x}');
        expect(formatMetadataValue({})).toBe('{}');
    });
});
