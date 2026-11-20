import { get2dEmbeddingsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { GetEmbeddings2dRequest } from '$lib/api/lightly_studio_local/types.gen';
import {
    parseEmbeddingsArrow,
    type EmbeddingsArrow
} from '$lib/components/PlotPanel/useArrowData/useArrowData';

import { createQuery, queryOptions } from '@tanstack/svelte-query';
import { isEqual } from 'lodash-es';

type EmbeddingsColorBy = GetEmbeddings2dRequest['color_by'];
type EmbeddingsAxes = GetEmbeddings2dRequest['axes'];

interface UseEmbeddingsOptions {
    enabled?: boolean;
    getIsComputing?: () => boolean;
    onCompute?: (compute: Promise<unknown>) => void;
}

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
    // The server keeps computing after an abort, and a second request conflicts with it.
    // TanStack aborts on unmount only if the signal is read, so a compute is not given it:
    // the fetch outlives a closed panel and a reopened panel joins it.
    const queryFn: typeof options.queryFn =
        typeof fetchPlot === 'function'
            ? (context) => {
                  if (!getIsComputing()) return fetchPlot(context);
                  const { client, queryKey, meta } = context;
                  // The query promise settles after the last retry, not after this attempt.
                  const compute = client.getQueryCache().find({ queryKey, exact: true })?.promise;
                  if (compute) onCompute(compute);
                  const signal = new AbortController().signal;
                  return fetchPlot({ client, queryKey, meta, signal });
              }
            : options.queryFn;
    return queryOptions({
        ...options,
        queryFn,
        enabled,
        // The status query refetches on focus and decides whether a compute may start.
        refetchOnWindowFocus: false,
        select: selectEmbeddingsArrow,
        structuralSharing: shareEqualLegend
    });
}

export function useEmbeddings(...params: Parameters<typeof getEmbeddingsQueryOptions>) {
    return createQuery(() => getEmbeddingsQueryOptions(...params));
}
