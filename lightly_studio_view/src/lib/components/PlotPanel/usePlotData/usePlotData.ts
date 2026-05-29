import { writable, type Writable } from 'svelte/store';
import { EmbeddingView, type Point } from 'embedding-atlas/svelte';
import type { ComponentProps } from 'svelte';
import type { ArrowData } from '../useArrowData/useArrowData';
import { getCategoryBySelection } from '../getCategoryBySelection/getCategoryBySelection';
import { resolveVisibleCategory } from '../resolveVisibleCategory/resolveVisibleCategory';
import { FILTERED_CATEGORY, NOT_FILTERED_CATEGORY } from '../plotCategories';

type PlotColumn = 'x' | 'y' | 'category';

type UsePlotDataReturn = {
    data: ComponentProps<typeof EmbeddingView>['data'];
    categoryColors?: ComponentProps<typeof EmbeddingView>['categoryColors'];
    error?: Writable<string | undefined>;
    selectedSampleIds: Writable<string[]>;
};

type Selection = Point[] | null;

/**
 * Resolves each point's displayed category from its full `color_categories` list, so a
 * multi-category sample falls back to its next visible category when one is toggled off.
 */
function resolveBaseCategories(
    data: ArrowData,
    hiddenCategories: ReadonlySet<number>,
    pointCount: number
): Uint8Array {
    const colorCategories = data.color_categories as number[][];
    const fulfilsFilter = data.fulfils_filter as ArrayLike<number>;

    const category = new Uint8Array(pointCount);
    for (let index = 0; index < pointCount; index++) {
        category[index] = resolveVisibleCategory(
            colorCategories[index],
            fulfilsFilter[index],
            hiddenCategories
        );
    }
    return category;
}

/**
 * Transforms Arrow data into plot-ready format with category assignments based on filters and selections.
 * Applies range selection to categorize points and tracks which sample IDs are selected.
 *
 * @param arrowData - Parsed Arrow data containing x/y coordinates, filter status, and sample IDs
 * @param rangeSelection - Optional polygon selection to further categorize points within the range
 * @param hasActiveFilter - When false, all points start as FILTERED_CATEGORY so range selection still works without a pre-existing filter
 * @param hiddenCategories - Categories toggled off in the legend; points fall back to their next visible category
 * @returns Object with formatted plot data, error store, and selected sample IDs store
 */
export function usePlotData({
    arrowData,
    rangeSelection,
    highlightedSampleIds = [],
    hasActiveFilter = true,
    hiddenCategories = new Set()
}: {
    arrowData: ArrowData;
    rangeSelection: Selection;
    highlightedSampleIds?: string[];
    hasActiveFilter?: boolean;
    hiddenCategories?: ReadonlySet<number>;
}): UsePlotDataReturn {
    const error = writable<string | undefined>();
    const plotData = writable<Record<PlotColumn, unknown>>();
    const selectedSampleIds = writable<string[]>([]);

    const data = arrowData;

    if (!data) {
        return { data: plotData, error, selectedSampleIds };
    }

    const pointCount = (data.x as Float32Array).length;
    let category = hasActiveFilter
        ? resolveBaseCategories(data, hiddenCategories, pointCount)
        : new Uint8Array(pointCount).fill(FILTERED_CATEGORY);
    const sampleIds = data.sample_id as string[];

    if (rangeSelection) {
        // Points inside the polygon keep their prevValue; points outside are demoted to NOT_FILTERED_CATEGORY.
        category = category.map(getCategoryBySelection(rangeSelection, data));

        // Collect selected sample ids: in-polygon filtered points have FILTERED_CATEGORY.
        const _ids = category.reduce<string[]>((acc, pointCategory, index) => {
            if (pointCategory !== NOT_FILTERED_CATEGORY) {
                acc.push(sampleIds[index]);
            }
            return acc;
        }, []);
        selectedSampleIds.update(() => _ids);
    } else if (highlightedSampleIds.length > 0) {
        const highlightedSampleIdSet = new Set(highlightedSampleIds);
        category = category.map((pointCategory, index) => {
            if (pointCategory === NOT_FILTERED_CATEGORY) {
                return pointCategory;
            }
            return highlightedSampleIdSet.has(sampleIds[index])
                ? pointCategory
                : NOT_FILTERED_CATEGORY;
        });
    }

    plotData.set({
        x: data.x,
        y: data.y,
        category
    });

    return {
        data: plotData,
        error,
        selectedSampleIds
    };
}
