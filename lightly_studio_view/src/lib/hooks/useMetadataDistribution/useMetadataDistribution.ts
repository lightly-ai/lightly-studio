import { getMetadataDistributionRouteOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type {
    MetadataDistributionRequest,
    MetadataDistributionView
} from '$lib/api/lightly_studio_local/types.gen';
import { createQuery, type CreateQueryResult } from '@tanstack/svelte-query';

/** The grid-filter union accepted by the distribution endpoint. */
export type MetadataDistributionFilter = MetadataDistributionRequest['filter'];

export interface UseMetadataDistributionParams {
    collectionId: string;
    key: string;
    /** Optional grid filter scoping the aggregation (e.g. one tag's samples). */
    filter?: MetadataDistributionFilter;
    /** Number of equal-width bins for numeric keys (backend default when omitted). */
    bins?: number;
    /** Skip the request while false (e.g. no key selected yet). */
    enabled?: boolean;
}

/**
 * Fetch the distribution of a single metadata key.
 *
 * Categorical keys yield `data.categorical` (value/count pairs including an
 * explicit `(none)` entry); numeric keys yield `data.bin_edges`/`data.counts`
 * plus `data.none_count`. `params` is a getter so the query stays reactive to
 * a changing key, filter, or bin count.
 */
export const useMetadataDistribution = (
    params: () => UseMetadataDistributionParams
): CreateQueryResult<MetadataDistributionView, Error> => {
    return createQuery(() => {
        const { collectionId, key, filter, bins, enabled = true } = params();
        return {
            ...getMetadataDistributionRouteOptions({
                path: { collection_id: collectionId, key },
                body: { filter: filter ?? null, bins }
            }),
            enabled: enabled && Boolean(collectionId) && Boolean(key)
        };
    });
};
