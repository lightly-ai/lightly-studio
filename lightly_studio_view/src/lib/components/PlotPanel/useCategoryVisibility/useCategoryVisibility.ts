import { derived, get, type Readable, type Writable } from 'svelte/store';
import { usePostHog } from '$lib/hooks';
import type { PlotColorByType } from '../PlotColorByPopover/usePlotColorByType/usePlotColorByType';
import {
    EXCLUDED_LEGEND_KEY,
    getHiddenCategories,
    getLegendKey,
    isReservedLegendKey
} from './legendKeys';

interface UseCategoryVisibilityParams {
    getCollectionId: () => string;
    getColorByType: () => PlotColorByType | null;
    colorLegend: Readable<Map<number, string>>;
    hiddenKeys: Writable<Set<string>>;
}

interface UseCategoryVisibilityReturn {
    hiddenCategories: Readable<Set<number>>;
    toggleCategoryVisibility: (category: number) => void;
    focusCategoryVisibility: (categories: number[], category: number) => void;
    clearForColorByMode: () => void;
}

/**
 * Tracks hidden plot categories and exposes focused visibility helpers for the PlotPanel.
 * The hidden set holds legend keys, so a hidden class stays hidden when the backend moves it
 * to another slot, and when it leaves the legend and comes back.
 */
export const useCategoryVisibility = ({
    getCollectionId,
    getColorByType,
    colorLegend,
    hiddenKeys
}: UseCategoryVisibilityParams): UseCategoryVisibilityReturn => {
    const { trackEvent } = usePostHog();
    const hiddenCategories = derived([hiddenKeys, colorLegend], ([$hiddenKeys, $colorLegend]) =>
        getHiddenCategories($hiddenKeys, $colorLegend)
    );

    const getKey = (category: number) => getLegendKey(category, get(colorLegend).get(category));

    const getToggledHiddenKeys = (currentHiddenKeys: ReadonlySet<string>, key: string) => {
        const nextHiddenKeys = new Set(currentHiddenKeys);
        if (nextHiddenKeys.has(key)) {
            nextHiddenKeys.delete(key);
        } else {
            nextHiddenKeys.add(key);
        }
        return nextHiddenKeys;
    };

    const getFocusedHiddenKeys = (
        currentHiddenKeys: ReadonlySet<string>,
        isolateKeys: string[],
        focusedKey: string
    ) => {
        // Keys hidden outside the isolate set are reserved rows or classes that left the
        // legend. Isolating keeps them hidden.
        const preservedHiddenKeys = [...currentHiddenKeys].filter(
            (hiddenKey) => !isolateKeys.includes(hiddenKey)
        );
        const visibleKeys = isolateKeys.filter((key) => !currentHiddenKeys.has(key));

        // Show all keeps only the reserved rows. A class that left the legend shows again, so it
        // does not come back hidden when the filter is removed.
        if (visibleKeys.length === 1 && visibleKeys[0] === focusedKey) {
            return new Set(preservedHiddenKeys.filter(isReservedLegendKey));
        }
        return new Set([
            ...preservedHiddenKeys,
            ...isolateKeys.filter((key) => key !== focusedKey)
        ]);
    };

    const toggleCategoryVisibility = (category: number) => {
        const key = getKey(category);
        if (key === undefined) return;
        trackEvent('legend_category_toggled', {
            collection_id: getCollectionId(),
            color_by_type: getColorByType(),
            action: get(hiddenKeys).has(key) ? 'show' : 'hide'
        });
        hiddenKeys.update((currentHiddenKeys) => getToggledHiddenKeys(currentHiddenKeys, key));
    };

    const focusCategoryVisibility = (categories: number[], category: number) => {
        const focusedKey = getKey(category);
        if (focusedKey === undefined) return;
        const isolateKeys = categories
            .map(getKey)
            .filter((key): key is string => key !== undefined);
        trackEvent('legend_category_isolated', {
            collection_id: getCollectionId(),
            color_by_type: getColorByType()
        });
        hiddenKeys.update((currentHiddenKeys) =>
            getFocusedHiddenKeys(currentHiddenKeys, isolateKeys, focusedKey)
        );
    };

    // Excluded means the same in every color-by mode. The other rows get new labels.
    const clearForColorByMode = () => {
        hiddenKeys.update(
            (currentHiddenKeys) =>
                new Set([...currentHiddenKeys].filter((key) => key === EXCLUDED_LEGEND_KEY))
        );
    };

    return {
        hiddenCategories,
        toggleCategoryVisibility,
        focusCategoryVisibility,
        clearForColorByMode
    };
};
