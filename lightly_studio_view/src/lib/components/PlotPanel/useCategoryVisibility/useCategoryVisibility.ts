import { writable, get, type Readable, type Writable } from 'svelte/store';
import { usePostHog } from '$lib/hooks';
import type { PlotColorByType } from '../PlotColorByPopover/usePlotColorByType/usePlotColorByType';

const RESERVED_CATEGORY_COUNT = 3;

/**
 * Hidden plot categories. Reserved rows keep their meaning across requests, so they are stored by
 * index. Colored slots are re-ranked by the backend on every request (e.g. after a selection), so
 * they are stored by legend label and mapped back to the current slots with
 * `resolveHiddenCategories`.
 */
interface HiddenCategoryState {
    reserved: ReadonlySet<number>;
    labels: ReadonlySet<string>;
}

interface UseCategoryVisibilityParams {
    getCollectionId: () => string;
    getColorByType: () => PlotColorByType | null;
    getColorLegend: () => ReadonlyMap<number, string>;
}

interface UseCategoryVisibilityReturn {
    hiddenState: Readable<HiddenCategoryState>;
    toggleCategoryVisibility: (category: number) => void;
    focusCategoryVisibility: (categories: number[], category: number) => void;
    resetCategoryVisibility: (preservedCategories?: number[]) => void;
    syncColorByMode: (colorByMode: string, preservedCategories?: number[]) => void;
}

interface CollectionVisibility {
    hiddenState: Writable<HiddenCategoryState>;
    /** Color-by mode the hidden labels belong to. */
    colorByMode: string | undefined;
}

// Per collection, so hidden categories survive the plot unmounting (closing the panel, opening
// a sample, switching tabs). In memory only, so they last for the session.
const visibilityByCollection = new Map<string, CollectionVisibility>();

const getCollectionVisibility = (collectionId: string): CollectionVisibility => {
    let visibility = visibilityByCollection.get(collectionId);
    if (!visibility) {
        visibility = {
            hiddenState: writable({ reserved: new Set(), labels: new Set() }),
            colorByMode: undefined
        };
        visibilityByCollection.set(collectionId, visibility);
    }
    return visibility;
};

const isReserved = (category: number) => category < RESERVED_CATEGORY_COUNT;

/** Maps the hidden state to the category indices of the given legend. */
export const resolveHiddenCategories = (
    state: HiddenCategoryState,
    colorLegend: ReadonlyMap<number, string> | null | undefined
): Set<number> => {
    const hidden = new Set(state.reserved);
    for (const [category, label] of colorLegend ?? []) {
        if (!isReserved(category) && state.labels.has(label)) {
            hidden.add(category);
        }
    }
    return hidden;
};

/**
 * Tracks hidden plot categories and exposes focused visibility helpers for the PlotPanel.
 * The collection is read once, when the hook is created.
 */
export const useCategoryVisibility = ({
    getCollectionId,
    getColorByType,
    getColorLegend
}: UseCategoryVisibilityParams): UseCategoryVisibilityReturn => {
    const { trackEvent } = usePostHog();
    const visibility = getCollectionVisibility(getCollectionId());
    const { hiddenState } = visibility;

    const getLabel = (category: number) => getColorLegend().get(category);

    const withCategories = (
        state: HiddenCategoryState,
        hiddenCategories: ReadonlySet<number>
    ): HiddenCategoryState => {
        // Labels of categories absent from the current legend stay hidden, so they are still
        // hidden when a later request brings them back.
        const legendLabels = new Set(getColorLegend().values());
        const labels = new Set([...state.labels].filter((label) => !legendLabels.has(label)));
        const reserved = new Set<number>();
        for (const category of hiddenCategories) {
            if (isReserved(category)) {
                reserved.add(category);
                continue;
            }
            const label = getLabel(category);
            if (label !== undefined) labels.add(label);
        }
        return { reserved, labels };
    };

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
        // Categories hidden outside the `categories` isolate set are reserved rows; keep them hidden.
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

    const updateHiddenCategories = (
        update: (currentHiddenCategories: ReadonlySet<number>) => ReadonlySet<number>
    ) => {
        hiddenState.update((state) =>
            withCategories(state, update(resolveHiddenCategories(state, getColorLegend())))
        );
    };

    const toggleCategoryVisibility = (category: number) => {
        const current = resolveHiddenCategories(get(hiddenState), getColorLegend());
        trackEvent('legend_category_toggled', {
            collection_id: getCollectionId(),
            color_by_type: getColorByType(),
            action: current.has(category) ? 'show' : 'hide'
        });
        updateHiddenCategories((hidden) => getToggledHiddenCategories(hidden, category));
    };

    const focusCategoryVisibility = (categories: number[], category: number) => {
        trackEvent('legend_category_isolated', {
            collection_id: getCollectionId(),
            color_by_type: getColorByType()
        });
        updateHiddenCategories((hidden) =>
            getFocusedHiddenCategories(hidden, categories, category)
        );
    };

    const resetCategoryVisibility = (preservedCategories: number[] = []) => {
        // Clears hidden labels; keeps the reserved rows the caller asks to preserve.
        hiddenState.update((state) => ({
            reserved: new Set(
                preservedCategories.filter((category) => state.reserved.has(category))
            ),
            labels: new Set()
        }));
    };

    const syncColorByMode = (colorByMode: string, preservedCategories: number[] = []) => {
        // A new color-by mode has other labels, so its change clears them. The same mode, e.g.
        // after the plot mounts again, keeps them.
        if (visibility.colorByMode === colorByMode) return;
        visibility.colorByMode = colorByMode;
        resetCategoryVisibility(preservedCategories);
    };

    return {
        hiddenState,
        toggleCategoryVisibility,
        focusCategoryVisibility,
        resetCategoryVisibility,
        syncColorByMode
    };
};
