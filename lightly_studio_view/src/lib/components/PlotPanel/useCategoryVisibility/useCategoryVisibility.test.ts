import { get, writable } from 'svelte/store';
import { describe, expect, it } from 'vitest';
import { useCategoryVisibility } from './useCategoryVisibility';

const setup = (legend: [number, string][]) => {
    const colorLegend = writable(new Map(legend));
    const visibility = useCategoryVisibility({
        getCollectionId: () => 'col_1',
        getColorByType: () => null,
        colorLegend,
        hiddenKeys: writable(new Set<string>())
    });
    return { colorLegend, ...visibility };
};

const CLASSES: [number, string][] = [
    [3, 'person'],
    [4, 'car'],
    [5, 'bus']
];

describe('useCategoryVisibility', () => {
    it('toggles hidden categories', () => {
        const { hiddenCategories, toggleCategoryVisibility } = setup(CLASSES);

        toggleCategoryVisibility(4);
        expect(get(hiddenCategories)).toEqual(new Set([4]));

        toggleCategoryVisibility(4);
        expect(get(hiddenCategories)).toEqual(new Set());
    });

    it('ignores a slot without a label', () => {
        const { hiddenCategories, toggleCategoryVisibility, focusCategoryVisibility } =
            setup(CLASSES);

        toggleCategoryVisibility(9);
        focusCategoryVisibility([3, 9], 9);

        expect(get(hiddenCategories)).toEqual(new Set());
    });

    it('focuses one category and restores all categories on a second focus', () => {
        const { hiddenCategories, focusCategoryVisibility } = setup(CLASSES);

        focusCategoryVisibility([3, 4, 5], 4);
        expect(get(hiddenCategories)).toEqual(new Set([3, 5]));

        focusCategoryVisibility([3, 4, 5], 4);
        expect(get(hiddenCategories)).toEqual(new Set());
    });

    it('preserves a hidden reserved row through both isolate branches', () => {
        const { hiddenCategories, toggleCategoryVisibility, focusCategoryVisibility } =
            setup(CLASSES);

        toggleCategoryVisibility(1);

        focusCategoryVisibility([3, 4, 5], 4);
        expect(get(hiddenCategories)).toEqual(new Set([1, 3, 5]));

        focusCategoryVisibility([3, 4, 5], 4);
        expect(get(hiddenCategories)).toEqual(new Set([1]));
    });

    it('shows the classes that left the legend after a show all', () => {
        const legend: [number, string][] = [...CLASSES, [6, 'truck']];
        const { colorLegend, hiddenCategories, focusCategoryVisibility } = setup(legend);
        focusCategoryVisibility([3, 4, 5, 6], 6);
        colorLegend.set(
            new Map([
                [3, 'person'],
                [6, 'truck']
            ])
        );

        focusCategoryVisibility([3, 6], 6);
        colorLegend.set(new Map(legend));

        expect(get(hiddenCategories)).toEqual(new Set());
    });

    it('keeps a hidden class hidden after the backend re-ranks slots', () => {
        const { colorLegend, hiddenCategories, toggleCategoryVisibility } = setup(CLASSES);

        toggleCategoryVisibility(4);
        colorLegend.set(
            new Map([
                [3, 'car'],
                [4, 'person']
            ])
        );

        expect(get(hiddenCategories)).toEqual(new Set([3]));
    });

    it('hides a class again when it comes back to the legend', () => {
        const { colorLegend, hiddenCategories, toggleCategoryVisibility } = setup(CLASSES);

        toggleCategoryVisibility(4);
        colorLegend.set(new Map([[3, 'person']]));
        expect(get(hiddenCategories)).toEqual(new Set());

        colorLegend.set(new Map([[5, 'car']]));
        expect(get(hiddenCategories)).toEqual(new Set([5]));
    });

    it('clears all but Excluded on a color-by mode change', () => {
        const { hiddenCategories, toggleCategoryVisibility, clearForColorByMode } = setup(CLASSES);
        [1, 2, 3].forEach(toggleCategoryVisibility);

        clearForColorByMode();

        expect(get(hiddenCategories)).toEqual(new Set([1]));
    });
});
