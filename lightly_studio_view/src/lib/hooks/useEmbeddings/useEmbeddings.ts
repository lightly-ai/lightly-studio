import {
    get2dEmbeddingsOptions,
    get2dEmbeddingsQueryKey
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { GetEmbeddings2dRequest } from '$lib/api/lightly_studio_local/types.gen';
import {
    parseEmbeddingsArrow,
    type EmbeddingsArrow
} from '$lib/components/PlotPanel/useArrowData/useArrowData';

import { shouldRetryQuery } from '$lib/api/shouldRetryQuery';
import {
    createQuery,
    hashKey,
    queryOptions,
    type QueryClient,
    type SkipToken
} from '@tanstack/svelte-query';
import { isEqual } from 'lodash-es';
import { isSamePlotLayout, type PlotLayoutKey } from './isSamePlotLayout';

type EmbeddingsColorBy = GetEmbeddings2dRequest['color_by'];
type EmbeddingsAxes = GetEmbeddings2dRequest['axes'];
type FetchPlot = Exclude<
    ReturnType<typeof get2dEmbeddingsOptions>['queryFn'],
    SkipToken | undefined
>;
type OnCompute = (compute: Promise<unknown>) => void;

interface PlotComputeOptions {
    getIsComputing?: () => boolean;
    /**
     * Called once when a compute request starts. The promise settles when the request ends, and
     * rejects if the compute fails.
     */
    onCompute?: OnCompute;
}

interface UseEmbeddingsParams extends PlotLayoutKey, PlotComputeOptions {
    filters: GetEmbeddings2dRequest['filters'] | null;
    enabled: boolean;
}

interface RunningCompute {
    collectionId: string;
    promise: Promise<unknown>;
}

// The server keeps computing after an abort, and a second request conflicts with it.
// So every request for a plot joins the compute that runs for its query key.
const runningComputes = new WeakMap<QueryClient, Map<string, RunningCompute>>();

type EmbeddingsQueryKey = ReturnType<typeof get2dEmbeddingsQueryKey>;

// parseAs: 'arrayBuffer' makes the response an ArrayBuffer at runtime, but its type is unknown.
// A module-level select keeps its identity, so the query parses each response once.
const selectEmbeddingsArrow = (response: unknown) => parseEmbeddingsArrow(response as ArrayBuffer);

const isEmbeddingsArrow = (value: unknown): value is EmbeddingsArrow =>
    value instanceof Object && 'legend' in value && value.legend instanceof Map;

// The plot resets its hidden classes when the legend object changes, so an equal legend keeps
// its previous object. Raw responses, which TanStack Query also passes here, stay as they are.
const shareEqualLegend = (previous: unknown, next: unknown): unknown => {
    if (!isEmbeddingsArrow(previous) || !isEmbeddingsArrow(next)) return next;
    if (!isEqual(previous.legend, next.legend)) return next;
    return { ...next, legend: previous.legend };
};

const getLayoutKey = ([{ path, body }]: EmbeddingsQueryKey): PlotLayoutKey => ({
    collectionId: path.collection_id,
    colorBy: body.color_by ?? null,
    axes: body.axes ?? null
});

/** Query options for the plot's 2D embeddings. A parse error in `select` is the query error. */
export function getEmbeddingsQueryOptions(
    collectionId: string,
    filters: GetEmbeddings2dRequest['filters'] | null,
    colorBy: EmbeddingsColorBy = null,
    axes: EmbeddingsAxes = null,
    { getIsComputing = () => false, onCompute = () => {} }: PlotComputeOptions = {}
) {
    const options = get2dEmbeddingsOptions({
        path: { collection_id: collectionId },
        body: { filters: filters ?? {}, color_by: colorBy, axes },
        // Not part of the query key: every user of this key must fetch an ArrayBuffer.
        parseAs: 'arrayBuffer'
    });
    const fetchPlot = options.queryFn;
    if (typeof fetchPlot !== 'function') throw new Error('The plot query has no query function.');
    // Set by the latest request, so a failed compute is not retried: the user agreed to one.
    let isComputeRequest = false;
    const queryFn: typeof fetchPlot = (context) => {
        isComputeRequest = getIsComputing();
        if (!isComputeRequest) return fetchPlot(context);
        return joinRunningCompute(context, fetchPlot, onCompute);
    };
    return queryOptions({
        ...options,
        queryFn,
        retry: (failureCount, error) => !isComputeRequest && shouldRetryQuery(failureCount, error),
        // The status query refetches on focus and decides whether a compute may start.
        refetchOnWindowFocus: false,
        select: selectEmbeddingsArrow,
        structuralSharing: shareEqualLegend
    });
}

// TanStack aborts on unmount only if the signal is read, so a compute gets a signal of its own:
// it outlives a closed panel, and a reopened panel joins it.
function joinRunningCompute(
    context: Parameters<FetchPlot>[0],
    fetchPlot: FetchPlot,
    onCompute: OnCompute
): Promise<unknown> {
    const { client, queryKey, meta } = context;
    const computes = runningComputes.get(client) ?? new Map<string, RunningCompute>();
    runningComputes.set(client, computes);
    const computeKey = hashKey(queryKey);
    const runningCompute = computes.get(computeKey);
    if (runningCompute) return runningCompute.promise;

    // The server saves one plot per collection, so a request with another filter, color-by or
    // axes waits for the running compute and then reads the saved plot. If it fails, so does this.
    const collectionId = queryKey[0].path.collection_id;
    const earlierComputes = [...computes.values()]
        .filter((compute) => compute.collectionId === collectionId)
        .map((compute) => compute.promise);
    const signal = new AbortController().signal;
    const fetchCompute = () => fetchPlot({ client, queryKey, meta, signal });
    const promise = Promise.all(earlierComputes).then(fetchCompute);
    computes.set(computeKey, { collectionId, promise });
    const endCompute = () => computes.delete(computeKey);
    void promise.then(endCompute, endCompute);
    onCompute(promise);
    return promise;
}

/**
 * Fetches the 2D embeddings for the plot. Call it once per plot: a filter change keeps the
 * previous points as placeholder data, but a new collection, color-by or axes does not,
 * because old colors or coordinates would be wrong.
 */
export function useEmbeddings(getParams: () => UseEmbeddingsParams) {
    return createQuery(() => {
        const { collectionId, filters, colorBy, axes, enabled, getIsComputing, onCompute } =
            getParams();
        const layout = { collectionId, colorBy, axes };
        return {
            ...getEmbeddingsQueryOptions(collectionId, filters, colorBy, axes, {
                getIsComputing,
                onCompute
            }),
            enabled,
            // The previous data is the raw response; `select` parses it again.
            placeholderData: (previousData, previousQuery) =>
                previousQuery && isSamePlotLayout(getLayoutKey(previousQuery.queryKey), layout)
                    ? previousData
                    : undefined
        };
    });
}
