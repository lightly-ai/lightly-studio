import { createQuery } from '@tanstack/svelte-query';
import type { TagSelectionOverlapBody } from '$lib/api/lightly_studio_local/types.gen';
import { getTagSelectionOverlapOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { getTagSelectionOverlap } from '$lib/api/lightly_studio_local/sdk.gen';

// Reports, per sample tag, how many of the currently selected samples already
// carry it. Used by the split dialog to warn which tags will be overwritten.
export const useSelectionTagOverlap = (
    getParams: () => {
        collectionId: string;
        filter: TagSelectionOverlapBody['filter'];
        /** Set to false to prevent the query from fetching. Default: true. */
        enabled?: boolean;
    }
) => {
    return createQuery(() => {
        const { collectionId, filter, enabled } = getParams();
        const requestOptions = {
            path: { collection_id: collectionId },
            body: { filter: filter ?? null }
        };

        return {
            ...getTagSelectionOverlapOptions(requestOptions),
            queryFn: async ({ signal }: { signal: AbortSignal }) => {
                const { data } = await getTagSelectionOverlap({
                    ...requestOptions,
                    signal,
                    throwOnError: true
                });
                return data;
            },
            ...(enabled !== undefined ? { enabled } : {})
        };
    });
};
