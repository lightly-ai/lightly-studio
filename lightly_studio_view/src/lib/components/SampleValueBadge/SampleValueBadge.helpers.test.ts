import { describe, expect, it } from 'vitest';
import { formatOrderValue, hasValueBadge } from './SampleValueBadge.helpers';

describe('formatOrderValue', () => {
    it('renders integers without decimals', () => {
        expect(formatOrderValue(5)).toBe('5');
    });

    it('renders non-integers with two decimals', () => {
        expect(formatOrderValue(0.75)).toBe('0.75');
        expect(formatOrderValue(1.5)).toBe('1.50');
    });
});

describe('hasValueBadge', () => {
    it('is true when either value is set', () => {
        expect(hasValueBadge(3, null)).toBe(true);
        expect(hasValueBadge(null, 0.9)).toBe(true);
    });

    it('is false when both are null or undefined', () => {
        expect(hasValueBadge(null, null)).toBe(false);
        expect(hasValueBadge()).toBe(false);
    });
});
