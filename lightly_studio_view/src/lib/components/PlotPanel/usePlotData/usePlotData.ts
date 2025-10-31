import { writable, type Writable } from 'svelte/store';
import { EmbeddingView, type Point } from 'embedding-atlas/svelte';
import type { ComponentProps } from 'svelte';
import type { ArrowData } from '../useArrowData/useArrowData';
import { getCategoryBySelection } from '../getCategoryBySelection/getCategoryBySelection';

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
 * @returns Object with formatted plot data, error store, and selected sample IDs store
 */
export function usePlotData({
    arrowData,
    rangeSelection
}: {
    arrowData: ArrowData;
    rangeSelection: Selection;
}): UsePlotDataReturn {
    const error = writable<string | undefined>();
    const plotData = writable<Record<PlotColumn, unknown>>();
    const selectedSampleIds = writable<string[]>([]);

    const data = arrowData;

    if (!data) {
        return { data: plotData, error, selectedSampleIds };
    }

    let category = data.fulfils_filter as Uint8Array;
    const sampleIds = data.sample_id as string[];

    if (rangeSelection) {
        const hasRangeSelection = typeof rangeSelection !== 'undefined';

        // if we have range selection, update category based on it
        if (hasRangeSelection) {
            category = category.map(getCategoryBySelection(rangeSelection, data));

            // collect selected sample ids by category
            const _ids = category.reduce<string[]>((acc, cat, index) => {
                if (cat === 2) {
                    acc.push(sampleIds[index]);
                }
                return acc;
            }, []);
            selectedSampleIds.update(() => _ids);
        }
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
