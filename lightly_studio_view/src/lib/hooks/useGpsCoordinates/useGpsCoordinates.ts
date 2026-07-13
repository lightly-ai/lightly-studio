import { getGpsCoordinatesRouteOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type {
    GpsCoordinateView,
    GpsCoordinatesRequest
} from '$lib/api/lightly_studio_local/types.gen';
import { createQuery, type CreateQueryResult } from '@tanstack/svelte-query';

/** The grid-filter union accepted by the GPS endpoint. */
export type GpsCoordinatesFilter = GpsCoordinatesRequest['filter'];

export interface UseGpsCoordinatesParams {
    collectionId: string;
    key: string;
    /** Optional grid filter scoping the returned samples to the active selection. */
    filter?: GpsCoordinatesFilter;
    /** Skip the request while false (e.g. no GPS key present). */
    enabled?: boolean;
}

/**
 * Fetch per-sample GPS coordinates (with sample tags) for the interactive map.
 *
 * `params` is a getter so the query stays reactive to a changing key or filter.
 */
export const useGpsCoordinates = (
    params: () => UseGpsCoordinatesParams
): CreateQueryResult<Array<GpsCoordinateView>, Error> => {
    return createQuery(() => {
        const { collectionId, key, filter, enabled = true } = params();
        return {
            ...getGpsCoordinatesRouteOptions({
                path: { collection_id: collectionId, key },
                body: { filter: filter ?? null }
            }),
            enabled: enabled && Boolean(collectionId) && Boolean(key)
        };
    });
};
