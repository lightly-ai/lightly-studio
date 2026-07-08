import { writable, type Writable } from 'svelte/store';
import { EmbeddingView, type Point } from 'embedding-atlas/svelte';
import type { ComponentProps } from 'svelte';
import type { ArrowData } from '../useArrowData/useArrowData';
import { getCategoryBySelection } from '../getCategoryBySelection/getCategoryBySelection';
import { resolveVisibleCategory } from '../resolveVisibleCategory/resolveVisibleCategory';
import {
    EXCLUDED_BY_FILTERS_CATEGORY,
    HIDDEN_CATEGORY,
    INCLUDED_BY_FILTERS_CATEGORY
} from '../plotCategories';

type PlotColumn = 'x' | 'y' | 'category';

// Filtered-out and hidden points land in reserved categories and must never be selected.
const isUnselectableCategory = (category: number): boolean =>
    category === EXCLUDED_BY_FILTERS_CATEGORY || category === HIDDEN_CATEGORY;

type UsePlotDataReturn = {
    data: ComponentProps<typeof EmbeddingView>['data'];
    categoryColors?: ComponentProps<typeof EmbeddingView>['categoryColors'];
    error?: Writable<string | undefined>;
    selectedSampleIds: Writable<string[]>;
};

type Selection = Point[] | null;

/**
 * Transforms Arrow data into plot-ready format with category assignments based on filters and selections.
 * Applies range selection to categorize points and tracks which sample IDs are selected.
 *
 * @param arrowData - Parsed Arrow data containing x/y coordinates, filter status, and sample IDs
 * @param rangeSelection - Optional polygon selection to further categorize points within the range
 * @param hasActiveFilter - When false, all points start as INCLUDED_BY_FILTERS_CATEGORY so range selection still works without a pre-existing filter
 * @param hiddenCategories - Categories toggled off in the legend; points fall back to their next visible category
 * @returns Object with formatted plot data, error store, and selected sample IDs store
 */
export function usePlotData({
    arrowData,
    rangeSelection,
    highlightRegion = null,
    highlightedSampleIds = [],
    hasActiveFilter = true,
    hiddenCategories = new Set()
}: {
    arrowData: ArrowData;
    rangeSelection: Selection;
    highlightRegion?: Selection;
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
    const colorCategories = data.color_categories as number[][];
    const fulfilsFilter = data.fulfils_filter as ArrayLike<number>;

    // Each point is displayed as its first visible category, so it falls back to the next
    // one when a category is toggled off. Without an active filter every point starts as
    // INCLUDED_BY_FILTERS_CATEGORY so range selection still works.
    let category = new Uint8Array(pointCount);
    if (hasActiveFilter) {
        for (let index = 0; index < pointCount; index++) {
            category[index] = resolveVisibleCategory(
                colorCategories[index],
                fulfilsFilter[index],
                hiddenCategories
            );
        }
    } else {
        category.fill(INCLUDED_BY_FILTERS_CATEGORY);
    }
    const sampleIds = data.sample_id as string[];

    if (rangeSelection) {
        // Points inside the polygon keep their prevValue; points outside are demoted to Excluded.
        category = category.map(getCategoryBySelection(rangeSelection, data));

        // Collect in-polygon ids, skipping points that are filtered out or hidden by a legend
        // toggle — a point the user cannot see must never be committed to the filter.
        const _ids = category.reduce<string[]>((acc, pointCategory, index) => {
            if (!isUnselectableCategory(pointCategory) && !hiddenCategories.has(pointCategory)) {
                acc.push(sampleIds[index]);
            }
            return acc;
        }, []);
        selectedSampleIds.update(() => _ids);
    } else if (highlightRegion) {
        // A region committed to the filter (e.g. the image lasso stored as embedding_region) has
        // no live rangeSelection to draw, but the plot must still reflect it: demote points
        // outside the polygon to Excluded so the in-selection points stay highlighted. The
        // resolved sample ids live server-side, so we don't recompute selectedSampleIds here.
        category = category.map(getCategoryBySelection(highlightRegion, data));
    } else if (highlightedSampleIds.length > 0) {
        const highlightedSampleIdSet = new Set(highlightedSampleIds);
        category = category.map((pointCategory, index) => {
            if (isUnselectableCategory(pointCategory)) {
                return pointCategory;
            }
            return highlightedSampleIdSet.has(sampleIds[index])
                ? pointCategory
                : EXCLUDED_BY_FILTERS_CATEGORY;
        });
    }

    // Hide on each point's final category, after demotion: a demoted point is hidden as Excluded,
    // not its pre-demotion bucket.
    if (hiddenCategories.size > 0) {
        category = category.map((pointCategory) =>
            hiddenCategories.has(pointCategory) ? HIDDEN_CATEGORY : pointCategory
        );
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
