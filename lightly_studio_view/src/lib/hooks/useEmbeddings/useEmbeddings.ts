import {
    get2dEmbeddingsOptions,
    get2dEmbeddingsQueryKey
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { GetEmbeddings2dRequest } from '$lib/api/lightly_studio_local/types.gen';
import {
    parseEmbeddingsArrow,
    type EmbeddingsArrow
} from '$lib/components/PlotPanel/useArrowData/useArrowData';

import { createQuery } from '@tanstack/svelte-query';
import { isEqual } from 'lodash-es';
import { isSamePlotLayout, type PlotLayoutKey } from './isSamePlotLayout';

type EmbeddingsColorBy = GetEmbeddings2dRequest['color_by'];
type EmbeddingsAxes = GetEmbeddings2dRequest['axes'];

interface UseEmbeddingsParams extends PlotLayoutKey {
    filters: GetEmbeddings2dRequest['filters'] | null;
    enabled: boolean;
}

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
    axes: EmbeddingsAxes = null
) {
    return {
        ...get2dEmbeddingsOptions({
            path: { collection_id: collectionId },
            body: { filters: filters ?? {}, color_by: colorBy, axes },
            // Not part of the query key: every user of this key must fetch an ArrayBuffer.
            parseAs: 'arrayBuffer'
        }),
        select: selectEmbeddingsArrow,
        structuralSharing: shareEqualLegend
    };
}

/**
 * Fetches the 2D embeddings for the plot. Call it once per plot: a filter change keeps the
 * previous points as placeholder data, but a new collection, color-by or axes does not,
 * because old colors or coordinates would be wrong.
 */
export function useEmbeddings(getParams: () => UseEmbeddingsParams) {
    return createQuery(() => {
        const { collectionId, filters, colorBy, axes, enabled } = getParams();
        const layout = { collectionId, colorBy, axes };
        return {
            ...getEmbeddingsQueryOptions(collectionId, filters, colorBy, axes),
            enabled,
            // The previous data is the raw response; `select` parses it again.
            placeholderData: (previousData, previousQuery) =>
                previousQuery && isSamePlotLayout(getLayoutKey(previousQuery.queryKey), layout)
                    ? previousData
                    : undefined
        };
    });
}
