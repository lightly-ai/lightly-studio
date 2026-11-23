import { get2dEmbeddingsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
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

type EmbeddingsColorBy = GetEmbeddings2dRequest['color_by'];
type EmbeddingsAxes = GetEmbeddings2dRequest['axes'];
type FetchPlot = Exclude<
    ReturnType<typeof get2dEmbeddingsOptions>['queryFn'],
    SkipToken | undefined
>;
type OnCompute = (compute: Promise<unknown>) => void;

interface UseEmbeddingsOptions {
    enabled?: boolean;
    getIsComputing?: () => boolean;
    /**
     * Called once when a compute request starts. The promise settles when the request ends, and
     * rejects if the compute fails.
     */
    onCompute?: OnCompute;
}

// The server keeps computing after an abort, and a second request conflicts with it.
// So every request for a plot joins the compute that runs for its query key.
const runningComputes = new WeakMap<QueryClient, Map<string, Promise<unknown>>>();

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

/** Query options for the plot's 2D embeddings. A parse error in `select` is the query error. */
export function getEmbeddingsQueryOptions(
    collectionId: string,
    filters: GetEmbeddings2dRequest['filters'] | null,
    colorBy: EmbeddingsColorBy = null,
    axes: EmbeddingsAxes = null,
    {
        enabled = true,
        getIsComputing = () => false,
        onCompute = () => {}
    }: UseEmbeddingsOptions = {}
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
        enabled,
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
    const computes = runningComputes.get(client) ?? new Map<string, Promise<unknown>>();
    runningComputes.set(client, computes);
    const computeKey = hashKey(queryKey);
    const runningCompute = computes.get(computeKey);
    if (runningCompute) return runningCompute;

    const signal = new AbortController().signal;
    const compute = Promise.resolve(fetchPlot({ client, queryKey, meta, signal }));
    computes.set(computeKey, compute);
    const endCompute = () => computes.delete(computeKey);
    void compute.then(endCompute, endCompute);
    onCompute(compute);
    return compute;
}

export function useEmbeddings(...params: Parameters<typeof getEmbeddingsQueryOptions>) {
    return createQuery(() => getEmbeddingsQueryOptions(...params));
}
