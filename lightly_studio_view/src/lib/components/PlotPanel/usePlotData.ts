import { writable, type Writable } from 'svelte/store';
import { EmbeddingView, type Point } from 'embedding-atlas/svelte';
import type { ComponentProps } from 'svelte';
import type { ArrowData } from './useArrowData';
import { isPointInPolygon } from '$lib/hooks/useEmbeddingSelection/isPointInPolygon';

// eslint-disable-next-line @typescript-eslint/no-unused-vars
const plotColumns = ['x', 'y', 'category'] as const;
type PlotColumn = (typeof plotColumns)[number];

type UsePlotDataReturn = {
    data: ComponentProps<typeof EmbeddingView>['data'];
    categoryColors?: ComponentProps<typeof EmbeddingView>['categoryColors'];
    error?: Writable<string | undefined>;
    selectedSampleIds: Writable<string[]>;
};

type Selection = Point[] | null;

/**
 * Prepare data to show in the plot
 *
 * @param dataBlob
 * @returns
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
        const _sampledSampleIds: string[] = [];

        const getCategoryBySelection =
            (selection: Selection) => (prevValue: number, index: number) => {
                if (!selection) {
                    return prevValue;
                }
                const x = (data.x as Float32Array)[index];
                const y = (data.y as Float32Array)[index];
                const isIntersected = isPointInPolygon(x, y, selection);
                return prevValue == 1 && isIntersected ? 1 : 0;
            };
        const hasRangeSelection = typeof rangeSelection !== 'undefined';

        // if we have range selection, update category based on it
        if (hasRangeSelection) {
            category = category.map(getCategoryBySelection(rangeSelection));
            category.forEach((cat, index) => {
                if (cat === 1) {
                    const sampleId = sampleIds[index];
                    _sampledSampleIds.push(sampleId);
                }
            });
            const _ids = category.reduce<string[]>((acc, cat, index) => {
                if (cat === 1) {
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
