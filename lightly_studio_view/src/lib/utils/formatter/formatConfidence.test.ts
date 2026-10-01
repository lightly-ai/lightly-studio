import { describe, expect, it } from 'vitest';
import { formatConfidence } from './formatConfidence';

describe('formatConfidence', () => {
    it('formats confidence with two decimal places', () => {
        expect(formatConfidence(0.876)).toBe('0.88');
    });

    it('returns null for missing confidence', () => {
        expect(formatConfidence(null)).toBeNull();
        expect(formatConfidence(undefined)).toBeNull();
    });
});
