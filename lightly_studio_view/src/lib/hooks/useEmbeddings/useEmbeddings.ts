import {
    get2dEmbeddingsOptions,
    get2dEmbeddingsQueryKey
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { GetEmbeddings2dRequest } from '$lib/api/lightly_studio_local/types.gen';
import {
    parseEmbeddingsArrow,
    type EmbeddingsArrow
} from '$lib/components/PlotPanel/useArrowData/useArrowData';

import { NoRetryError } from '$lib/api/NoRetryError';
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
     * Called when a request starts a compute. A request that joins a running compute does not
     * call it. The promise settles when the compute ends, and rejects if the compute fails.
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
class PlotComputeRegistry {
    readonly #computes = new Map<string, RunningCompute>();

    join(computeKey: string): Promise<unknown> | undefined {
        return this.#computes.get(computeKey)?.promise;
    }

    /**
     * Starts a compute when the running computes of its collection end, because the server saves
     * one plot per collection. If one of them fails, this compute fails without a request.
     */
    start(computeKey: string, collectionId: string, fetchCompute: () => unknown): Promise<unknown> {
        const earlierComputes = [...this.#computes.values()]
            .filter((compute) => compute.collectionId === collectionId)
            .map((compute) => compute.promise);
        const promise = Promise.all(earlierComputes).then(fetchCompute);
        this.#computes.set(computeKey, { collectionId, promise });
        const end = () => this.#end(computeKey);
        void promise.then(end, end);
        return promise;
    }

    #end(computeKey: string): void {
        this.#computes.delete(computeKey);
    }
}

const computeRegistries = new WeakMap<QueryClient, PlotComputeRegistry>();

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
    const queryFn: typeof fetchPlot = (context) => {
        if (!getIsComputing()) return fetchPlot(context);
        return joinRunningCompute(context, fetchPlot, onCompute).catch(failWithoutRetry);
    };
    return queryOptions({
        ...options,
        queryFn,
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
    const registry = computeRegistries.get(client) ?? new PlotComputeRegistry();
    computeRegistries.set(client, registry);
    const computeKey = hashKey(queryKey);
    const runningCompute = registry.join(computeKey);
    if (runningCompute) return runningCompute;

    const signal = new AbortController().signal;
    const fetchCompute = () => fetchPlot({ client, queryKey, meta, signal });
    const compute = registry.start(computeKey, queryKey[0].path.collection_id, fetchCompute);
    onCompute(compute);
    return compute;
}

// The user agreed to one compute, so a failed compute is not retried.
const failWithoutRetry = (error: unknown): never => {
    throw new NoRetryError(error);
};

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
