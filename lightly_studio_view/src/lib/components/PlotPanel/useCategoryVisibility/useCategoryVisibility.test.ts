import { get } from 'svelte/store';
import { describe, expect, it } from 'vitest';
import { resolveHiddenCategories, useCategoryVisibility } from './useCategoryVisibility';

const setup = (initialLegend: [number, string][] = []) => {
    let legend = new Map<number, string>(initialLegend);
    const visibility = useCategoryVisibility({
        getCollectionId: () => 'col_1',
        getColorByType: () => null,
        getColorLegend: () => legend
    });
    const hidden = () => resolveHiddenCategories(get(visibility.hiddenState), legend);
    const setLegend = (next: [number, string][]) => {
        legend = new Map(next);
    };
    return { ...visibility, hidden, setLegend };
};

describe('useCategoryVisibility', () => {
    it('toggles hidden categories', () => {
        const { hidden, toggleCategoryVisibility } = setup([[3, 'dog']]);

        toggleCategoryVisibility(3);
        expect(hidden()).toEqual(new Set([3]));

        toggleCategoryVisibility(3);
        expect(hidden()).toEqual(new Set());
    });

    it('keeps a hidden category hidden when the backend re-ranks the color slots', () => {
        const { hidden, toggleCategoryVisibility, setLegend } = setup([
            [3, 'dog'],
            [4, 'cat'],
            [5, 'fox']
        ]);

        toggleCategoryVisibility(4);
        // A selection re-ranks the legend: "cat" moves to slot 3.
        setLegend([
            [3, 'cat'],
            [4, 'fox'],
            [5, 'dog']
        ]);
        expect(hidden()).toEqual(new Set([3]));

        // A legend without "cat" shows nothing hidden, and "cat" is hidden again once it returns.
        setLegend([[3, 'dog']]);
        expect(hidden()).toEqual(new Set());
        setLegend([
            [3, 'dog'],
            [4, 'cat']
        ]);
        expect(hidden()).toEqual(new Set([4]));
    });

    it('focuses one category and restores all categories on a second focus', () => {
        const { hidden, focusCategoryVisibility } = setup([
            [3, 'dog'],
            [4, 'cat'],
            [5, 'fox']
        ]);
        const categories = [3, 4, 5];

        focusCategoryVisibility(categories, 4);
        expect(hidden()).toEqual(new Set([3, 5]));

        focusCategoryVisibility(categories, 4);
        expect(hidden()).toEqual(new Set());
    });

    it('preserves a hidden reserved row through both isolate branches', () => {
        const { hidden, toggleCategoryVisibility, focusCategoryVisibility } = setup([
            [3, 'dog'],
            [4, 'cat'],
            [5, 'fox']
        ]);
        // Colored isolate universe; reserved row 1 lives outside it.
        const categories = [3, 4, 5];

        toggleCategoryVisibility(1);

        // Isolate-to-siblings branch: reserved row 1 survives alongside the hidden siblings.
        focusCategoryVisibility(categories, 4);
        expect(hidden()).toEqual(new Set([1, 3, 5]));

        // Show-all branch: colored hidden state clears but reserved row 1 survives.
        focusCategoryVisibility(categories, 4);
        expect(hidden()).toEqual(new Set([1]));
    });

    it('preserves requested reserved rows on reset while clearing hidden labels', () => {
        const { hidden, resetCategoryVisibility, toggleCategoryVisibility } = setup([[4, 'dog']]);

        toggleCategoryVisibility(1); // reserved row, stable by index
        toggleCategoryVisibility(4); // color slot, stored by label

        resetCategoryVisibility([1, 2]);

        // Reserved row 1 survives; "dog" clears; row 2 was never hidden so it is not added.
        expect(hidden()).toEqual(new Set([1]));
    });
});
