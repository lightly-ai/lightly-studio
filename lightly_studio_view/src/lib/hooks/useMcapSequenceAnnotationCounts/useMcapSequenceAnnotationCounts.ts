import { createQuery } from '@tanstack/svelte-query';
import { countMcapSequenceAnnotationsByCollectionOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type {
    CountMcapSequenceAnnotationsByCollectionResponse,
    McapSequenceFilter,
    ReadMcapSequenceCountAnnotationsRequest
} from '$lib/api/lightly_studio_local';

interface McapSequenceAnnotationCountsParams {
    collectionId: string;
    filter?: McapSequenceFilter | null;
}

interface McapSequenceAnnotationCountsRequest {
    path: { collection_id: string };
    body: ReadMcapSequenceCountAnnotationsRequest;
}

export function buildMcapSequenceAnnotationCountsRequest({
    collectionId,
    filter
}: McapSequenceAnnotationCountsParams): McapSequenceAnnotationCountsRequest {
    return { path: { collection_id: collectionId }, body: { filter } };
}

/**
 * Counts the MCAP sequences of each annotation class. A sequence counts for a class when
 * one of its groups has an annotation of that class.
 */
export const useMcapSequenceAnnotationCounts = (
    getParams: () => McapSequenceAnnotationCountsParams & {
        /** Set to false to prevent the query from fetching. Default: true. */
        enabled?: boolean;
    }
) =>
    createQuery(() => {
        const { enabled = true, ...params } = getParams();
        return {
            ...countMcapSequenceAnnotationsByCollectionOptions(
                buildMcapSequenceAnnotationCountsRequest(params)
            ),
            // Keep the previous counts while the request for a new filter runs, so that the
            // counts do not flash empty.
            placeholderData: (
                previousData: CountMcapSequenceAnnotationsByCollectionResponse | undefined
            ) => previousData,
            enabled
        };
    });
