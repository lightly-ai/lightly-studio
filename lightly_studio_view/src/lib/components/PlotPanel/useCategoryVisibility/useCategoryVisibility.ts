import { writable, type Readable } from 'svelte/store';

interface UseCategoryVisibilityReturn {
    hiddenCategories: Readable<Set<number>>;
    toggleCategoryVisibility: (category: number) => void;
    focusCategoryVisibility: (categories: number[], category: number) => void;
    resetCategoryVisibility: () => void;
}

/**
 * Tracks hidden plot categories and exposes focused visibility helpers for the PlotPanel.
 */
export const useCategoryVisibility = (): UseCategoryVisibilityReturn => {
    const hiddenCategories = writable(new Set<number>());

    const getToggledHiddenCategories = (
        currentHiddenCategories: ReadonlySet<number>,
        category: number
    ) => {
        const nextHiddenCategories = new Set(currentHiddenCategories);

        if (nextHiddenCategories.has(category)) {
            nextHiddenCategories.delete(category);
        } else {
            nextHiddenCategories.add(category);
        }

        return nextHiddenCategories;
    };

    const getFocusedHiddenCategories = (
        currentHiddenCategories: ReadonlySet<number>,
        categories: number[],
        category: number
    ) => {
        // `categories` is the colored-only isolate universe; anything hidden outside it is a
        // reserved row whose state must survive isolation.
        const preservedHiddenCategories = [...currentHiddenCategories].filter(
            (hiddenCategory) => !categories.includes(hiddenCategory)
        );

        const visibleCategories = categories.filter(
            (visibleCategory) => !currentHiddenCategories.has(visibleCategory)
        );

        if (visibleCategories.length === 1 && visibleCategories[0] === category) {
            return new Set<number>(preservedHiddenCategories);
        }

        return new Set([
            ...preservedHiddenCategories,
            ...categories.filter((visibleCategory) => visibleCategory !== category)
        ]);
    };

    const toggleCategoryVisibility = (category: number) => {
        hiddenCategories.update((currentHiddenCategories) =>
            getToggledHiddenCategories(currentHiddenCategories, category)
        );
    };

    const focusCategoryVisibility = (categories: number[], category: number) => {
        hiddenCategories.update((currentHiddenCategories) =>
            getFocusedHiddenCategories(currentHiddenCategories, categories, category)
        );
    };

    const resetCategoryVisibility = () => {
        hiddenCategories.set(new Set<number>());
    };

    return {
        hiddenCategories,
        toggleCategoryVisibility,
        focusCategoryVisibility,
        resetCategoryVisibility
    };
};
