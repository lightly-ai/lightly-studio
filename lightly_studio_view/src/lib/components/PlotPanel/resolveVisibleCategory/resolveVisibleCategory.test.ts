import { describe, it, expect } from 'vitest';
import { resolveVisibleCategory } from './resolveVisibleCategory';

describe('resolveVisibleCategory', () => {
    it('returns EXCLUDED_BY_FILTERS_CATEGORY (1) when the point does not fulfil the filter', () => {
        expect(resolveVisibleCategory([3, 4], 0, new Set())).toBe(1);
    });

    it('returns the first category when none are hidden', () => {
        expect(resolveVisibleCategory([3, 4], 1, new Set())).toBe(3);
    });

    it('returns INCLUDED_BY_FILTERS_CATEGORY (2) when the point has no categories', () => {
        expect(resolveVisibleCategory([], 1, new Set())).toBe(2);
    });

    it('falls back to the next visible category when the first is hidden', () => {
        expect(resolveVisibleCategory([3, 4], 1, new Set([3]))).toBe(4);
    });

    it('falls back to INCLUDED_BY_FILTERS_CATEGORY (2) when the only category is hidden', () => {
        expect(resolveVisibleCategory([3], 1, new Set([3]))).toBe(2);
    });

    it('falls back to INCLUDED_BY_FILTERS_CATEGORY (2) when all categories are hidden', () => {
        expect(resolveVisibleCategory([3, 4], 1, new Set([3, 4]))).toBe(2);
    });

    it('ignores the filter when resolving a hidden fallback', () => {
        expect(resolveVisibleCategory([3, 4, 5], 1, new Set([3, 4]))).toBe(5);
    });
});
