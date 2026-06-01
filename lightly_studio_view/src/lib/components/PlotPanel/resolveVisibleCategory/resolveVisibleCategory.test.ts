import { describe, it, expect } from 'vitest';
import { resolveVisibleCategory } from './resolveVisibleCategory';

describe('resolveVisibleCategory', () => {
    it('returns NOT_FILTERED_CATEGORY (0) when the point does not fulfil the filter', () => {
        expect(resolveVisibleCategory([2, 3], 0, new Set())).toBe(0);
    });

    it('returns the first category when none are hidden', () => {
        expect(resolveVisibleCategory([2, 3], 1, new Set())).toBe(2);
    });

    it('returns FILTERED_CATEGORY (1) when the point has no categories', () => {
        expect(resolveVisibleCategory([], 1, new Set())).toBe(1);
    });

    it('falls back to the next visible category when the first is hidden', () => {
        expect(resolveVisibleCategory([2, 3], 1, new Set([2]))).toBe(3);
    });

    it('falls back to FILTERED_CATEGORY (1) when the only category is hidden', () => {
        expect(resolveVisibleCategory([2], 1, new Set([2]))).toBe(1);
    });

    it('falls back to FILTERED_CATEGORY (1) when all categories are hidden', () => {
        expect(resolveVisibleCategory([2, 3], 1, new Set([2, 3]))).toBe(1);
    });

    it('ignores the filter when resolving a hidden fallback', () => {
        expect(resolveVisibleCategory([2, 3, 4], 1, new Set([2, 3]))).toBe(4);
    });
});
