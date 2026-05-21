import { get } from 'svelte/store';
import { describe, expect, it } from 'vitest';
import { useCategoryVisibility } from './useCategoryVisibility';

describe('useCategoryVisibility', () => {
    it('toggles hidden categories', () => {
        const { hiddenCategories, toggleCategoryVisibility } = useCategoryVisibility();

        toggleCategoryVisibility(2);
        expect(get(hiddenCategories)).toEqual(new Set([2]));

        toggleCategoryVisibility(2);
        expect(get(hiddenCategories)).toEqual(new Set());
    });

    it('focuses one category and restores all categories on a second focus', () => {
        const { hiddenCategories, focusCategoryVisibility } = useCategoryVisibility();
        const categories = [2, 3, 4];

        focusCategoryVisibility(categories, 3);
        expect(get(hiddenCategories)).toEqual(new Set([2, 4]));

        focusCategoryVisibility(categories, 3);
        expect(get(hiddenCategories)).toEqual(new Set());
    });

    it('resets hidden categories', () => {
        const { hiddenCategories, resetCategoryVisibility, toggleCategoryVisibility } =
            useCategoryVisibility();

        toggleCategoryVisibility(4);
        resetCategoryVisibility();

        expect(get(hiddenCategories)).toEqual(new Set());
    });
});
