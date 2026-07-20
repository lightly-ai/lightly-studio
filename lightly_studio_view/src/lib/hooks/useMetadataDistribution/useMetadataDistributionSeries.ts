import {
    getMetadataDistributionRouteOptions,
    getNnDistanceDistributionRouteOptions
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { MetadataDistributionView } from '$lib/api/lightly_studio_local/types.gen';
import type { CategoryCount, ChartMode, ChartSeries } from '$lib/components/BarChart';
import { getSeriesColor } from '$lib/utils';
import { createQueries } from '@tanstack/svelte-query';
import type { MetadataDistributionFilter } from './useMetadataDistribution';

const NONE_LABEL = '(none)';

/** One comparison series to fetch (e.g. the current selection or a single tag). */
export interface MetadataDistributionSeriesInput {
    /** Stable id (tag id, or 'current' for the active selection). */
    id: string;
    /** Legend label shown for this series. */
    label: string;
    /** Grid filter scoping this series' samples (null = whole collection). */
    filter: MetadataDistributionFilter;
}

export interface UseMetadataDistributionSeriesParams {
    collectionId: string;
    /**
     * The metadata key to aggregate; queries stay disabled until it is set.
     * Ignored (and not required) when `endpoint` is `'nn_distance'`.
     */
    key: string | undefined;
    /** One entry per overlaid series, in display order. */
    series: MetadataDistributionSeriesInput[];
    /** Equal-width bins for numeric keys (backend default when omitted). */
    bins?: number;
    /**
     * Which endpoint to fetch from. `'metadata'` (default) aggregates the metadata
     * `key`; `'nn_distance'` fetches the computed nearest-neighbor distance
     * histogram, which needs no key.
     */
    endpoint?: 'metadata' | 'nn_distance';
    /** Skip all requests while false. */
    enabled?: boolean;
}

export interface MetadataDistributionSeriesResult {
    /** Fetched series (colored, aligned by input order); empty while loading. */
    series: ChartSeries[];
    /** Chart form derived from the key type; undefined until first result. */
    chartMode: ChartMode | undefined;
    isLoading: boolean;
    isError: boolean;
}

const formatBinEdge = (value: number): string => {
    if (!Number.isFinite(value)) return '';
    if (Number.isInteger(value)) return String(value);
    return value.toFixed(2).replace(/\.?0+$/, '');
};

/**
 * Turn a distribution response into the chart's `CategoryCount[]`: categorical
 * value/count pairs pass through; numeric bins become `lo–hi` range labels with
 * an explicit `(none)` bucket appended when some samples miss the key.
 */
export const distributionToCategoryCounts = (view: MetadataDistributionView): CategoryCount[] => {
    if (view.kind === 'categorical') {
        return (view.categorical ?? []).map((entry) => ({
            label: entry.value,
            count: entry.count
        }));
    }
    const edges = view.bin_edges ?? [];
    const counts = view.counts ?? [];
    const data: CategoryCount[] = counts.map((count, index) => ({
        label: `${formatBinEdge(edges[index])}–${formatBinEdge(edges[index + 1])}`,
        count
    }));
    if ((view.none_count ?? 0) > 0) {
        data.push({ label: NONE_LABEL, count: view.none_count ?? 0 });
    }
    return data;
};

/**
 * Fractional position of `mean` along the histogram's category axis, where each
 * numeric bin occupies one category band centered on its integer index. Returns
 * `undefined` when there are no bins to place it against.
 *
 * Bin `i` spans `[edges[i], edges[i + 1]]` and is centered at category index `i`,
 * so its band covers `[i - 0.5, i + 0.5]`; a mean at the bin's left edge maps to
 * `i - 0.5`, at its center to `i`, at its right edge to `i + 0.5`.
 */
export const meanCategoryIndex = (edges: number[], mean: number): number | undefined => {
    if (edges.length < 2) return undefined;
    const clamped = Math.min(Math.max(mean, edges[0]), edges[edges.length - 1]);
    let bin = 0;
    while (bin < edges.length - 2 && clamped >= edges[bin + 1]) bin += 1;
    const width = edges[bin + 1] - edges[bin];
    const fraction = width > 0 ? (clamped - edges[bin]) / width : 0.5;
    return bin + (fraction - 0.5);
};

/** Shape one distribution view into a colored chart series (aligned by input order). */
const toChartSeries = (
    input: MetadataDistributionSeriesInput,
    view: MetadataDistributionView,
    index: number
): ChartSeries => {
    const categoryIndex =
        view.mean != null ? meanCategoryIndex(view.bin_edges ?? [], view.mean) : undefined;
    return {
        id: input.id,
        label: input.label,
        color: getSeriesColor(index),
        data: distributionToCategoryCounts(view),
        mean:
            view.mean != null && categoryIndex !== undefined
                ? { value: view.mean, categoryIndex }
                : undefined
    };
};

/**
 * Metadata endpoint: one filtered request per series. Numeric keys share an x-axis
 * because the backend computes bin edges over the key's global range.
 */
const useMetadataSeries = (
    params: () => UseMetadataDistributionSeriesParams
): MetadataDistributionSeriesResult =>
    createQueries(() => {
        const { collectionId, key, series, bins, endpoint = 'metadata', enabled = true } = params();
        const active = enabled && endpoint === 'metadata' && Boolean(collectionId) && Boolean(key);
        return {
            queries: series.map((input) => ({
                ...getMetadataDistributionRouteOptions({
                    path: { collection_id: collectionId, key: key ?? '' },
                    body: { filter: input.filter ?? null, bins }
                }),
                enabled: active
            })),
            combine: (results): MetadataDistributionSeriesResult => {
                const chartSeries: ChartSeries[] = [];
                let chartMode: ChartMode | undefined;
                results.forEach((result, index) => {
                    const view = result.data;
                    if (!view) return;
                    chartMode ??= view.kind === 'numeric' ? 'histogram' : 'bar';
                    chartSeries.push(toChartSeries(series[index], view, index));
                });
                return {
                    series: chartSeries,
                    chartMode,
                    isLoading: results.some((result) => result.isLoading),
                    isError: results.some((result) => result.isError)
                };
            }
        };
    });

/**
 * Nearest-neighbor endpoint: all series in a *single* request. Each series' distances
 * are computed within its own samples (small per-tag matrices), and the backend returns
 * histograms that already share one set of bin edges.
 */
const useNnDistanceSeries = (
    params: () => UseMetadataDistributionSeriesParams
): MetadataDistributionSeriesResult =>
    createQueries(() => {
        const { collectionId, series, bins, endpoint = 'metadata', enabled = true } = params();
        const active = enabled && endpoint === 'nn_distance' && Boolean(collectionId);
        return {
            queries: [
                {
                    ...getNnDistanceDistributionRouteOptions({
                        path: { collection_id: collectionId },
                        body: {
                            series: series.map((input) => ({ filter: input.filter ?? null })),
                            bins
                        }
                    }),
                    enabled: active
                }
            ],
            combine: ([result]): MetadataDistributionSeriesResult => {
                const views = result.data ?? [];
                return {
                    series: views.map((view, index) => toChartSeries(series[index], view, index)),
                    chartMode: views.length > 0 ? 'histogram' : undefined,
                    isLoading: result.isLoading,
                    isError: result.isError
                };
            }
        };
    });

/**
 * Fetch the distribution of one metadata key (or the computed nearest-neighbor
 * distance) across several comparison series and shape them for the multi-series
 * BarChart. `params` is a getter so the queries stay reactive to a changing key,
 * series list, or bin count.
 *
 * Both endpoints' queries are wired unconditionally (so hook order is stable) and
 * gated by `endpoint`; only the active one runs and its result is returned.
 */
export const useMetadataDistributionSeries = (
    params: () => UseMetadataDistributionSeriesParams
): MetadataDistributionSeriesResult => {
    const metadata = useMetadataSeries(params);
    const nnDistance = useNnDistanceSeries(params);
    const isNnDistance = params().endpoint === 'nn_distance';
    return isNnDistance ? nnDistance : metadata;
};
