import { describe, expect, it } from 'vitest';
import { formatInteger } from './formatInteger';

describe('formatInteger', () => {
    it('groups thousands with separators', () => {
        expect(formatInteger(1234567)).toBe('1,234,567');
    });

    it('leaves small integers unchanged', () => {
        expect(formatInteger(42)).toBe('42');
    });
});
