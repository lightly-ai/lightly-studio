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

    it('preserves a hidden reserved row through both isolate branches', () => {
        const { hiddenCategories, toggleCategoryVisibility, focusCategoryVisibility } =
            useCategoryVisibility();
        // Colored isolate universe; reserved row 1 lives outside it.
        const categories = [3, 4, 5];

        toggleCategoryVisibility(1);

        // Isolate-to-siblings branch: reserved row 1 survives alongside the hidden siblings.
        focusCategoryVisibility(categories, 4);
        expect(get(hiddenCategories)).toEqual(new Set([1, 3, 5]));

        // Show-all branch: colored hidden state clears but reserved row 1 survives.
        focusCategoryVisibility(categories, 4);
        expect(get(hiddenCategories)).toEqual(new Set([1]));
    });

    it('resets hidden categories', () => {
        const { hiddenCategories, resetCategoryVisibility, toggleCategoryVisibility } =
            useCategoryVisibility();

        toggleCategoryVisibility(4);
        resetCategoryVisibility();

        expect(get(hiddenCategories)).toEqual(new Set());
    });

    it('preserves requested reserved rows on reset while clearing remapped color slots', () => {
        const { hiddenCategories, resetCategoryVisibility, toggleCategoryVisibility } =
            useCategoryVisibility();

        toggleCategoryVisibility(1); // reserved row, stable by index
        toggleCategoryVisibility(4); // color slot, remapped on refresh

        resetCategoryVisibility([1, 2]);

        // Reserved row 1 survives; color slot 4 clears; row 2 was never hidden so it is not added.
        expect(get(hiddenCategories)).toEqual(new Set([1]));
    });
});
