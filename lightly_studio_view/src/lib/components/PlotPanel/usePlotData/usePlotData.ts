import { writable, type Writable } from 'svelte/store';
import { EmbeddingView, type Point } from 'embedding-atlas/svelte';
import type { ComponentProps } from 'svelte';
import type { ArrowData } from '../useArrowData/useArrowData';
import { getCategoryBySelection } from '../getCategoryBySelection/getCategoryBySelection';
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
 * Transforms Arrow data into plot-ready format with category assignments based on filters and selections.
 * Applies range selection to categorize points and tracks which sample IDs are selected.
 *
 * @param arrowData - Parsed Arrow data containing x/y coordinates, filter status, and sample IDs
 * @param rangeSelection - Optional polygon selection to further categorize points within the range
 * @param hasActiveFilter - When false, all points start as FILTERED_CATEGORY so range selection still works without a pre-existing filter
 * @returns Object with formatted plot data, error store, and selected sample IDs store
 */
export function usePlotData({
    arrowData,
    rangeSelection,
    highlightedSampleIds = [],
    hasActiveFilter = true
}: {
    arrowData: ArrowData;
    rangeSelection: Selection;
    highlightedSampleIds?: string[];
    hasActiveFilter?: boolean;
}): UsePlotDataReturn {
    const error = writable<string | undefined>();
    const plotData = writable<Record<PlotColumn, unknown>>();
    const selectedSampleIds = writable<string[]>([]);

    const data = arrowData;

    if (!data) {
        return { data: plotData, error, selectedSampleIds };
    }

    let category = hasActiveFilter
        ? (data.fulfils_filter as Uint8Array)
        : new Uint8Array((data.x as Float32Array).length).fill(FILTERED_CATEGORY);
    const sampleIds = data.sample_id as string[];

    if (rangeSelection) {
        category = category.map(getCategoryBySelection(rangeSelection, data));

        const _ids = category.reduce<string[]>((acc, pointCategory, index) => {
            if (pointCategory === FILTERED_CATEGORY) {
                acc.push(sampleIds[index]);
            }
            return acc;
        }, []);
        selectedSampleIds.update(() => _ids);
    } else if (highlightedSampleIds.length > 0) {
        const highlightedSampleIdSet = new Set(highlightedSampleIds);
        category = category.map((pointCategory, index) => {
            if (pointCategory !== FILTERED_CATEGORY) {
                return pointCategory;
            }
            return highlightedSampleIdSet.has(sampleIds[index])
                ? FILTERED_CATEGORY
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
